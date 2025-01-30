'''
Utilities for testing purposes only.
'''

def flatten(nested_list):
    '''
    Flatten a 2D array without importing a dependency or using numpy arrays.
    '''
    return [item for sublist in nested_list for item in sublist]
