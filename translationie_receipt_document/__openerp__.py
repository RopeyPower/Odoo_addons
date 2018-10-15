# -*- coding: utf-8 -*-
{
	'name' : 'Receipt Document',
	'version' : '1.0',
	'summary' : 'Print Receipts for Payments',
	'sequence': 30,
	'description' : """
Allows printing of a receipt for a payment from the payment form.
	""",
	
	'category' : 'Accounting & Finance',
	'website' : '',
	'depends' : ['account','sale'],
	'data': [
		# 'views/account_payment_view.xml',
		'views/email_template.xml',
		'views/res_config_view.xml',
	],
}