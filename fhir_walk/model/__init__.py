
import pdb
def unwrap_bundle(response):
    """If the resource type is 'Bundle', return the contents of that bundle. 

    If the contents are a list with a length of one, return the item instead of the list"""
    if 'resourceType' in response and response['resourceType'] == 'Bundle':
        if response['total'] > 0:
            contents = response['entry']

            if len(contents) == 1:
                return contents[0]

            return contents
        return []

    # Basically do nothing if the resourceType isn't bundle
    return response