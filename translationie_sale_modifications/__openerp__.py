# -*- coding: utf-8 -*-
{
    'name': "translationie_sale_modifications",

    'summary': """
        Modifications to sale, sale_service and mail modules for the purpose of modeling translation.ie workflow """,

    'description': """
        Adds source and language columns to sale order lines. Allows the creation 
        of quotations from emails by selecting 'Sales Order' under Create a new record
        under incoming mail server configuration
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['mail','sale_service','translationie_invoice_modifications'],
    'data': [
        # 'security/ir.model.access.csv',
        'translationie_sale_modifications_view.xml',
		'translationie_sale_modifications_report.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}