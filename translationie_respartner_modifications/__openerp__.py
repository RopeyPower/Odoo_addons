# -*- coding: utf-8 -*-
{
    'name': "translationie_respartner_modifications",

    'summary': """
        Modifies res.partner object to include extra information for customers and vendors required by translation.ie""",

    'description': """
        Adds legacy sage account field to customer form for customers who are companies.
		Adds translator status, rate information and timezone to vendor form.
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['x_res', 'account','mail'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'translationie_respartner_mod_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}