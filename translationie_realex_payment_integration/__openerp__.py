# -*- coding: utf-8 -*-
{
    'name': "translationie_realex_payment_integration",

    'summary': """
        Integration with Hosted Payment Page provided by Realex Payments""",

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website','x_res','translationie_project_modifications','translationie_fetch_reply_emails'],

    # always loaded
    'data': [
		'security/ir.model.access.csv',
		'security/user_groups.xml',
		'views/config_views.xml',
		'views/confirmation_page.xml',
		'views/payment_page.xml',
		'views/sale_order_uid_view.xml',
		'views/daily_batch_close_cron.xml',
		'views/realex_statement_view.xml',
		'views/email_templates.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}