# -*- coding: utf-8 -*-
{
    'name': "Translation.ie VAT report",

    'summary': """
        Extends the Account Tax Cash Basis module to correctly create the cash based vat records with the marked payment date.""",

    'description': """
        Potential TODO: add report that outputs a vat3 style report.
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account_tax_cash_basis'],
    'data': [
        # 'security/ir.model.access.csv',
		'wizard/vat_report_wizard.xml',
		'views/account_tax_view.xml',
		'views/vat_report_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}