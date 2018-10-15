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
	'depends' : ['account'],
	'data': [
		'views/report_receipt.xml',
		'views/account_payment_report.xml',
	],
}