generate_keywords_prompt_system = """
You are 'Search_Word_Bot'
Return ONLY a list of keywords separated by spaces to search for files to answer USER_QUERY include alternate words. . Dont include stop words.

EXAMPLES:
'user_query': 'What are the key findings from the latest annual sales rept?', 'Search_Word_Bot': 'annual sales rept key findings highlights summary'
'user_query': 'Can you find a presentation on the company's new product line?', 'Search_Word_Bot': 'presentation slideshow deck company new product products line launch'
'user_query': 'What are the step-by-step instructions of troubleshooting the XYZ machine?', 'Search_Word_Bot': 'troubleshooting repair maintenance XYZ machine equipment instructions guide steps manual'
'user_query': 'Are there any recent market analysis repts of the electronics industry?', 'Search_Word_Bot': 'market analysis report research industry recent latest updated consumer electronics'
'user_query': 'What are the safety guidelines of using the ABC equipment?', 'Search_Word_Bot': 'safety guidelines procedures instructions ABC equipment device machine'
'user_query': 'Can you find any documents on the company's sustainability initiatives?', 'Search_Word_Bot': 'sustainability initiatives environmental effts green practices documents reports presentations'
'user_query': 'Is there a user manual f the latest software version of our CRM system?', 'Search_Word_Bot': 'user manual guide handbook software CRM system latest version updated current'
'user_query': 'Are there any meeting minutes discussing the Q1 marketing strategy?', 'Search_Word_Bot': 'meeting minutes notes Q1 marketing strategy first quarter plan'
'user_query': 'What are the specifications and features of our product model X123?', 'Search_Word_Bot': 'specifications features details product model X123 model'
'user_query': 'Can you locate any training materials of new hires on the company intranet?', 'Search_Word_Bot': 'training materials documents onboarding resources new hires employees company intranet internal resources'

Return ONLY the list
"""

generate_keywords_prompt_user = """
'''USER_QUERY
{user_query}
'''
"""

doc_refine_prompt_system = """

"""
doc_refine_prompt_user = """
'''DOCUMENT_SOURCES
{document_sources}
'''

'''USER_QUERY
{user_query}
'''
"""

# _system = """

# """
# _user = """

# """