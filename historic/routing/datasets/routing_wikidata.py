import json
import os
import sys
from SPARQLWrapper import SPARQLWrapper, JSON
import json

endpoint_url = "https://query.wikidata.org/sparql"

query = """SELECT ?placeLabel ?distance ?place ?location  WHERE {
    SERVICE wikibase:around { 
      ?place wdt:P625 ?location . 
      bd:serviceParam wikibase:center "Point(11.121475411318539 46.06749951056832)"^^geo:wktLiteral . 
      bd:serviceParam wikibase:radius "2" . 
      bd:serviceParam wikibase:distance ?distance .
    } 
    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}  LIMIT 100"""

WIKIDATA_LOCATIONS_JSON = 'data/wikidata_points.json'

def download_wikidata_points(log=False):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    qry_result =  sparql.query().convert()
    results_list = qry_result["results"]["bindings"]
    results = []
    for n, result in enumerate(results_list, 1):
        results.append({
            key: result[key]['value']
            for key in ['placeLabel', 'distance', 'place', 'location']
        })
        if log:
            name = result['placeLabel']['value']
            loc = result['location']['value'] # long, lat
            print(f'{str(n).rjust(3)}: {name}: {loc}')
    
    with open(WIKIDATA_LOCATIONS_JSON, 'w') as f:
        json.dump(results, f, indent=3, ensure_ascii=False)

    return results

def read_wikidata_locations(log=False):
    
    if not os.path.exists(WIKIDATA_LOCATIONS_JSON):
        download_wikidata_points()

    with open(WIKIDATA_LOCATIONS_JSON) as f:
        results_list = json.load(f)
    results = {}
    for result in results_list:
        name = result['placeLabel']
        loc = result['location']
        long_lat = loc.split('Point(')[1].split(')')[0]
        long, lat = [float(x) for x in long_lat.split(' ')]
        results[name] = [long, lat]
        if log:
            print(f'{name}: {long},{lat}')
    return results

if __name__ == "__main__":
    download_wikidata_points(log=True)
    

    

    
