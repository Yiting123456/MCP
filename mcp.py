# server.py
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource, ResourceTemplate, Tool, TextContent
import requests
import os
from requests import Session
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import warnings
import sys
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 禁用不安全请求警告
warnings.filterwarnings("ignore", category=InsecureRequestWarning)



metris_uri = os.getenv('METRIS_URI')
metris_username = os.getenv('METRIS_USERNAME')
metris_password = os.getenv('METRIS_PASSWORD')

base_uri = metris_uri 

data = {"username": metris_username, "password": metris_password}

def get_metris_token():
    config = {
        "base_url": base_uri
    }
    uri = f"{base_uri}/api/account/authenticate"
    response = requests.post(uri, json=data, verify=False) 
    token_data = response.json()
    token = token_data.get("id")
    headers = {"Authorization":f"Bearer {token}"}
    return config, token, headers

def get_tags():
    uri = f'{base_uri}/api/configuration/tags'
    response = requests.get(uri, headers=headers, verify=False)
    return response.text

def get_trend_values(params):
    uri = f'{base_uri}/api/historian/v02/trendvalues'
    response = requests.get(uri, headers=headers, params=params, verify=False)
    return response.text

def get_tag_values(ids):
    uri = f'{base_uri}/api/historian/v02/tagvalues'
    params = {'ids': ids}
    values = requests.get(uri, headers=headers, params=params,verify=False)
    return values.text

def get_tags_by_name(tag_names):
    tags = get_tags()
    return [t for t in tags if t['name'] in tag_names] 


def get_tags_information():
    """获取所有标签的基本信息"""
    # 获取配置和token
    config, token, headers = get_metris_token()
    tags_infor = get_tags()
    
    tags = [tag.get('name', None) for tag in tags_infor] 
    criticalityID = [tag.get('id', None) for tag in tags_infor]  
    descriptions = [tag.get('description', None) for tag in tags_infor] 
    engLow = [tag.get('engLow', None) for tag in tags_infor]  
    engHigh = [tag.get('engHigh', None) for tag in tags_infor] 
    engUnits = [tag.get('engUnits', None) for tag in tags_infor] 
    lowerNormalLimit = [tag.get('lowerNormalLimit', None) for tag in tags_infor]  
    lowerSpecificationLimit = [tag.get('lowerSpecificationLimit', None) for tag in tags_infor]  
    upperNormalLimit = [tag.get('upperNormalLimit', None) for tag in tags_infor]  
    upperSpecificationLimit = [tag.get('upperSpecificationLimit', None) for tag in tags_infor] 

    return tags, criticalityID, descriptions, engLow, engHigh, engUnits, lowerNormalLimit, lowerSpecificationLimit, upperNormalLimit, upperSpecificationLimit


def get_tag_values(tag_id_list):
    """获取指定标签的实时值"""
    if not tag_id_list:
        return []
        
    config, token, headers = get_metris_token()
    tags, criticalityID, descriptions, engLow, engHigh, engUnits, lowerNormalLimit, lowerSpecificationLimit, upperNormalLimit, upperSpecificationLimit = get_tags_information()

    tag_values = get_tag_values(tag_id_list)
    values = [tag['value'] for tag in tag_values]
    
    result = []
    
    for id in tag_id_list:
        try:
            i = tag_id_list.index(id)
            value = values[i]
            
            j = criticalityID.index(id)
            description = descriptions[j]
            
            engLowValue = engLow[j]
            engHighValue = engHigh[j]
            engUnitsValue = engUnits[j]
            lowerNormalLimitValue = lowerNormalLimit[j]
            lowerSpecificationLimitValue = lowerSpecificationLimit[j]
            upperNormalLimitValue = upperNormalLimit[j]
            upperSpecificationLimitValue = upperSpecificationLimit[j]
            
            if value is None or lowerSpecificationLimitValue is None or upperSpecificationLimitValue is None:
                status = "Invalid Data"
            else:
                if value < lowerSpecificationLimitValue or value > upperSpecificationLimitValue:
                    status = "Alarm"
                elif (lowerSpecificationLimitValue < value < lowerNormalLimitValue) or (upperNormalLimitValue < value < upperSpecificationLimitValue):
                    status = "Warning"
                else:
                    status = "Normal"
            
            result.append({
                'id': id,
                'description': description,
                'value': value,
                'units': engUnitsValue,
                'status': status,  
                'lowerNormalLimitValue': lowerNormalLimitValue, 
                'lowerSpecificationLimitValue': lowerSpecificationLimitValue,  
                'upperNormalLimitValue': upperNormalLimitValue,  
                'upperSpecificationLimitValue': upperSpecificationLimitValue  
            })
        except Exception as e:
            print(f"处理标签 {id} 时出错: {str(e)}")
            result.append({
                'id': id,
                'error': str(e)
            })
    
    return result


def get_trend_values(tag_id_list):
    """获取指定标签的趋势数据"""
    if not tag_id_list:
        raise ValueError("Cannot get the related trend values, please check the tag or give me more information about the tag.")
    
    config, token, headers = get_metris_token()

    end_time = datetime.now()
    start_time = end_time - timedelta(days=15) 
    result = []
    for id in tag_id_list:
        try:
            parameters = {
                'tagid': id,
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'timeshift': 0,
                'interpolationmethod': 1,  # 0=step, 1=linear, 7=cubic_spline_robust
                'interpolationresolution': 1080,
                'interpolationresolutiontype': 0,  # 0=points, 1=ticks
                'aggregatefunction': 0,  # 0=average, 1=min, 2=max, etc.
                'trackingreferencestep': None
                }
            trend_values = get_trend_values(parameters)
            result.append({"id": id, "trend_values": trend_values})
        except Exception as e:
            print(f"获取标签 {id} 趋势数据时出错: {str(e)}")
            result.append({"id": id, "error": str(e)})
    
    return result


def find_best_match(description: str) -> list:
    """基于文本相似度查找最匹配的标签"""
    tags, criticalityID, descriptions, engLow, engHigh, engUnits, lowerNormalLimit, lowerSpecificationLimit, upperNormalLimit, upperSpecificationLimit = get_tags_information()
    
    if not descriptions:
        return []
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(descriptions + [description])
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    idx = cosine_similarities.argmax()
    
    if cosine_similarities[idx] < 0.1:  
        return []
    
    return [criticalityID[idx]]

def find_best_match_by_tagname(tagname: str) -> list:
    """基于文本相似度查找最匹配的标签"""
    tags, criticalityID, descriptions, engLow, engHigh, engUnits, lowerNormalLimit, lowerSpecificationLimit, upperNormalLimit, upperSpecificationLimit = get_tags_information()

    if not tags:
        return []
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(tags + [tagname])
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    idx = cosine_similarities.argmax()
    
    if cosine_similarities[idx] < 0.7:  
        return []
    
    return [criticalityID[idx]]


app = FastMCP(
    name="mcp-server-metris",
    description="MCP Server for Metris and Client Industry Data",
    version="0.1.0"
)


@app.tool(name="get_real_tag_values_from_description", description="根据查询参数获取实时标签值，传入一个参数query是用户的查询")
def get_real_tag_values(query: str) -> list[TextContent]:
    """根据查询获取实时标签值"""
    if not query:
        raise ValueError("Query is required")
    
    query = f"EXPLAIN {query}"

    tag_id_list = find_best_match(query)
    
    if not tag_id_list:
        return [TextContent(type="text", text="No related tags found.")]

    tag_values = get_tag_values(tag_id_list)
    return [TextContent(type="text", text=str(tag_values))]

@app.tool(name="get_real_tag_values_from_tagname", description="根据查询参数获取实时标签值，传入一个参数query是用户的查询，比如标签03R01B01-L1.GAIN")
def get_real_tag_values_from_tagname(query: str) -> list[TextContent]:
    """根据查询获取实时标签值"""
    if not query:
        raise ValueError("Query is required")

    tag_id_list = find_best_match_by_tagname(query)

    if not tag_id_list:
        return [TextContent(type="text", text="No related tags found.")]

    tag_values = get_tag_values(tag_id_list)
    return [TextContent(type="text", text=str(tag_values))]

@app.tool(name="get_trend_values", description="根据查询参数获取标签趋势数据，传入一个参数query是用户的描述")
def get_real_trend_values(query: str) -> list[TextContent]:
    """根据查询获取标签趋势数据"""
    if not query:
        raise ValueError("Query is required")
    
    query = f"EXPLAIN {query}"
    tag_id_list = find_best_match(query)
    
    if not tag_id_list:
        return [TextContent(type="text", text="No related tags found.")]
    
    trend_values = get_trend_values(tag_id_list)
    return [TextContent(type="text", text=str(trend_values))]


@app.prompt()
def generate_get_real_values_prompt(query: list) -> str:
    """为客户端生成一个提示，查找特定标签的实时值"""
    return f"""使用 get_tag_values 工具查找以下标签的实时值：{', '.join(query)}。

请按照以下步骤操作：
1. 首先，使用 get_tag_values_from_description(query={query}) 获取实时值。
   - 如果标签不存在或无法获取值，请返回相应的错误信息。
   - 如果标签存在且获取到了值，请返回标签的实时值。
2. 如果第一步标签不存在或无法获取值，请使用 get_tag_values_from_tagname(query={query}) 获取实时值。
    - 如果标签存在且获取到了值，请返回以下信息：
        - 标签名称
        - 当前值
3. 如果标签不存在或无法获取值，请返回相应的错误信息。
4. 最后，将所有标签的实时值整理成一个易于理解的格式，并返回给用户。
请注意，结果全部用中文回答。
"""
