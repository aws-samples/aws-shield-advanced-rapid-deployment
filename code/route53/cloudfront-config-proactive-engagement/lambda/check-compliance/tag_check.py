import json, os, copy

def tag_check(resourceTags, include=True):
    checkTags = json.loads(os.environ['checkTags'])
    tagResults = copy.copy(checkTags)
    if include == True:
        for cTag in checkTags:
            for rTag in resourceTags:
                #Check each check Tag where there is both a key and value, if match remove from list
                if (rTag == cTag):
                    tagResults.remove(cTag)
                #CHeck where only a tag key is provided, if match remove from list
                if "Value" not in cTag:
                    if cTag['Key'] == rTag['Key']:
                        tagResults.remove(cTag)
            #success if when the checkTags is an empty array, i.e. []
        if tagResults == []:
            return (True)
        else:
            return (False)
    elif include == False:
        tagResults = True
        for cTag in checkTags:
            for rTag in resourceTags:
                #Check each check Tag where there is both a key and value, if match remove from list
                if (rTag == cTag):
                    tagResults = True
                #CHeck where only a tag key is provided, if match remove from list
                if "Value" not in cTag:
                    if cTag['Key'] == rTag['Key']:
                        tagResults = True
            #success if when the checkTags is an empty array, i.e. []
        return (tagResults)