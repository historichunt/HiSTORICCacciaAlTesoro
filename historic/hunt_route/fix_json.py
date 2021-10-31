import json

if __name__ == "__main__":
    json_file = 'data/Trento_DM_GOOGLE.json'
    data = json.load(open(json_file))
    coordinates = data['coordinates']
    new_coordinates = []
    for c in coordinates:
        new_coordinates.append([c[1],c[0]])
    data['coordinates'] = new_coordinates
    with open(json_file, 'w') as fout:
        json.dump(data, fout, ensure_ascii=False, indent=3)