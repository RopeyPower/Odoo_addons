# -*- coding: utf-8 -*-
{
    'name': "translationie_invoice_modifications",

    'summary': """
        Modifies the invoice lines and the invoice form.""",

    'description': """
        Adds source and target language as well as monetary VAT amount to each invoice line.
		Adds a purchase order number field to the invoice form.
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['x_res','account',],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'translationie_invoice_mod_view.xml',
		'translationie_invoice_mod_report.xml',
		'po_email_template.xml',
		'res_company_invoice_mod_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}