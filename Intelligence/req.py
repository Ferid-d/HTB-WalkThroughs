import requests

# request
def req(url):
    resp = requests.get(url) 
    if resp.status_code == 200:
        print("Find: ", middle + ext )
        return resp.content
    else:
        return None
 
# # set url
base = 'http://intelligence.htb/documents/2020-'

ext = '-upload.pdf'

for i in range(12):
    i += 1
    if i < 10:
        mon  = '0' + str(i)
    else:
        mon = str(i)   
    # day
    for j in range(31):
        j += 1
        if j <10:
            day = '0' + str(j)
        else:
            day = str(j)
        middle = mon  + '-' + day
        url = base + middle + ext
        
        content = req(url)
        #write to host
        if content:
            with open(middle + ext , 'wb') as f:
                f.write(content)
