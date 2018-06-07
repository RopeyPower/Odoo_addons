# -*- coding: utf-8 -*-
{
    'name': "fetch_reply_emails",

    'summary': """
        Retrieves emails from assigned mailboxes that are replies to a mail originating 
		from odoo or are part of a thread beginning with an email from odoo.""",

    'description': """
        This module searches every mailbox configured as an incoming mail gateway in odoo for emails that have an 
		In-Reply_To header that matches the message_id of a mail sent from odoo. For any emails found it adds them to
		the source document of the message it is replying to.
		
		Only works for mailboxes that support IMAP
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'fetch_reply_emails_data.xml',
        'fetch_reply_emails_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}