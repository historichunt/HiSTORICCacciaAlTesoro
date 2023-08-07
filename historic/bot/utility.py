import re
import textwrap

from google.cloud.ndb import utils
import requests
from io import BytesIO
import cv2
import numpy as np


def check_email(text_input):
    email_split = text_input.split()
    return any(re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]+$", e) for e in email_split)

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def answer_is_almost_correct(guess, solution_set):
    solution_set_word = [x for x in solution_set if len(x)>=4]
    if any(x.isdigit() for x in solution_set_word):
        return False    
    if min(len(x) for x in solution_set_word) <= 3:
        return False
    if any(x in solution_set_word for x in guess.split()):
        return True
    if min(levenshtein(guess, s) for s in solution_set_word) <= 2:
        return True

def import_url_csv_to_dict_list(url_csv, remove_new_line_escape=True): #escape_markdown=True
    import csv
    import requests
    r = requests.get(url_csv)
    spreadSheetTsv = r.content.split('\n')
    reader = csv.DictReader(spreadSheetTsv)
    if remove_new_line_escape:
        return [{k:v.replace('\\n', '\n') for k,v in dict.items()} for dict in reader]
    return [dict for dict in reader]


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def is_int_between(s, low, high):
    if not is_int(s):
        return False
    sInt = int(s)
    if sInt>=low and sInt<=high:
        return True
    return False

def is_float_between(s, low, high):
    if not is_float(s):
        return False
    sFloat = float(s)
    if sFloat>=low and sFloat<=high:
        return True
    return False

def append_num_to_filename(filename):
    if '_' in filename: 
        prefix, suffix = filename.rsplit('_', 1)
        if is_int(suffix):
            num = int(suffix)
            return f'{prefix}_{num+1}'
    return f'{filename}_1'
    

re_letters_space = re.compile('^[a-zA-Z ]+$')
re_digits = re.compile(r'^\d+$')

def hasOnlyLettersAndSpaces(s):
    return re_letters_space.match(s) != None

def hasOnlyDigits(s):
    return re_digits.match(s) != None

def randomAlphaNumericString(lenght):
    import random, string
    x = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(lenght))
    return x

def representsFloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def numberEnumeration(list):
    return [(str(x[0]), x[1]) for x in enumerate(list, 1)]


def letterEnumeration(list):
    return [(chr(x[0] + 65), x[1]) for x in enumerate(list, 0)]  #chd(65) = 'A'


def getIndexIfIntOrLetterInRange(input, max):
    if is_int(input):
        result = int(input)
        if result in range(1, max + 1):
            return result
    if input in list(map(chr, range(65, 65 + max))):
        return ord(input) - 64  # ord('A') = 65
    return None


def make_2d_array(data_list, length=2):
    return [data_list[i:i+length] for i in range(0, len(data_list), length)]

def distribute_elements_max_size(seq, maxSize=5):
    if len(seq)==0:
        return []
    lines = len(seq) / maxSize
    if len(seq) % maxSize > 0:
        lines += 1
    avg = len(seq) / float(lines)
    out = []
    last = 0.0
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    return out


def segmentArrayOnMaxChars(array, maxChar=20, ignoreString=None):
    #logging.debug('selected_tokens: ' + str(selected_tokens))
    result = []
    lineCharCount = 0
    currentLine = []
    for t in array:
        t_strip = t.replace(ignoreString, '') if ignoreString and ignoreString in t else t
        t_strip_size = len(t_strip.decode('utf-8'))
        newLineCharCount = lineCharCount + t_strip_size
        if not currentLine:
            currentLine.append(t)
            lineCharCount = newLineCharCount
        elif newLineCharCount > maxChar:
            #logging.debug('Line ' + str(len(result)+1) + " " + str(currentLine) + " tot char: " + str(lineCharCount))
            result.append(currentLine)
            currentLine = [t]
            lineCharCount = t_strip_size
        else:
            lineCharCount = newLineCharCount
            currentLine.append(t)
    if currentLine:
        #logging.debug('Line ' + str(len(result) + 1) + " " + str(currentLine) + " tot char: " + str(lineCharCount))
        result.append(currentLine)
    return result

reSplitSpace = re.compile(r"\s")

def splitTextOnSpaces(text):
    return reSplitSpace.split(text)

def escape_markdown(text):
    for char in '*_`[':
        text = text.replace(char, '\\'+char)
    return text

def containsMarkdown(text):
    for char in '*_`[':
        if char in text:
            return True
    return False

# minutes should be positive
def getHourMinFromMin(minutes):
    hh = int(minutes / 60)
    mm = minutes % 60
    return hh, mm


def getSiNoFromBoolean(bool_value):
    return 'SI' if bool_value else 'NO'

def getTimeStringFormatHHMM(minutes, rjust=False):
    hh, mm = getHourMinFromMin(abs(minutes))
    #return "{}h {}min".format(str(hh).zfill(2), str(mm).zfill(2))
    sign = '-' if minutes<0 else ''
    signHH = sign+str(hh)
    if rjust:
        signHH = signHH.rjust(3)
    return "{}:{}".format(signHH, str(mm).zfill(2))

def unindent(s):
    return re.sub('[ ]+', ' ', textwrap.dedent(s))

def roundup(x, upTo):
    import math
    return int(math.ceil(x / float(upTo))) * upTo

def emptyStringIfNone(x):
    return '' if x==None else x

def emptyStringIfZero(x):
    return '' if x==0 else x

def flatten(L):
    ret = []
    for i in L:
        if isinstance(i,list):
            ret.extend(flatten(i))
        else:
            ret.append(i)
    return ret

def format_distance(dst_km):
    if (dst_km>=10):
        return str(round(dst_km, 0)) + " Km"
    if (dst_km>=1):
        return str(round(dst_km, 1)) + " Km"
    return str(int(dst_km * 1000)) + " m"

def make_list_of_list(L):
    result = [[l] for l in L]
    return result

def remove_duplicates_from_list(list):
    no_dupicated_list = []
    for x in list:
        if x not in no_dupicated_list:
            no_dupicated_list.append(x)
    return no_dupicated_list

def sec_to_hms(elapsed_sec):
    mins, sec = divmod(elapsed_sec, 60)
    hour, mins = divmod(mins, 60)
    time_str = "%d:%02d:%02d" % (hour, mins, sec)
    return time_str

def read_qr_from_url(file_url):    
    img_content = requests.get(file_url).content
    img_array = np.asarray(bytearray(img_content), dtype=np.uint8)    
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    detect = cv2.QRCodeDetector()
    value, _, _ = detect.detectAndDecode(img) 
    return value # full code potentially including html address    

def qr_matches(goal, target):
    if 'QR_' in target:
        return goal == target.rsplit('QR_',1)[-1]    
    # last field after last forward slash (not necessary)
    return goal == target.rsplit('/',1)[-1]

def create_qr(text, transparent) -> None:
    import qrcode
    import io
    """Create QR from the user message."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    
    if transparent:
        img = img.convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[0] == 255 and item[1] == 255 and item[2] == 255:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)

        img.putdata(newData)
        format='WEBP'
    else:
        format='JPEG'

    # tmp_filename = "tmp_qrcode.webp"
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)    
    return img_bytes.read() # convert to byte-like object

def get_str_param_boolean(d, param):
    return d.get(param, 'False').lower() in ['true', '1', 't', 'y', 'yes']

def get_lat_lon_from_string(latlong_string):
    return [float(x) for x in latlong_string.split(',')]