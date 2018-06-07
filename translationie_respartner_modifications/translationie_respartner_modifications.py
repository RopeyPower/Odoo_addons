# -*- coding: utf-8 -*-

from openerp import models, fields, api

class translationie_respartner_modifications(models.Model):
	_inherit = 'res.partner'
	_name = 'res.partner'
	
	x_native = fields.Many2one(string='Native Language', comodel_name='x_res.languages')
	x_second_lang = fields.Many2one(string='Second Language', comodel_name='x_res.languages')
	x_third_lang = fields.Many2one(string='Third Language', comodel_name='x_res.languages')
	x_fourth_lang = fields.Many2one(string='Fourth Language', comodel_name='x_res.languages')
	
	x_language_pair = fields.One2many(string='Language Pairs', comodel_name='x_res.languages.pairs', inverse_name='x_translator')
	
	x_legacy_account = fields.Char(string='SAGE Account')

	x_specialisation = fields.Text(string='Specialisation')
	x_status = fields.Selection(selection=[('good','Green: 1. Consistent Positive Feedback 2. Trusted Translator'),('acceptable','Yellow:  1. Expensive 2. Limited Availability 3. Problems with Formatting Documents 4. Late Delivery'),('poor','Orange: 1. Non-Professional Behaviour 2. Poor Quality Translations'),('unavailable','Pink: 1. Currently on holidays/temporarily inactive.'),('blacklist','Red: 1. Blacklisted - Do Not Use'),('unused','Grey: Has not been used in quite some time i.e. over a year.')], string='Translator Status')
	x_timezone = fields.Selection(selection=[('GMT+0','[GMT +0]'),('GMT+1','[GMT +1]'),('GMT+2','[GMT +2]'),('GMT+3','[GMT +3]'),('GMT+4','[GMT +4]'),('GMT+5','[GMT +5]'),('GMT+6','[GMT +6]'),('GMT+7','[GMT +7]'),('GMT+8','[GMT +8]'),('GMT+9','[GMT +9]'),('GMT+10','[GMT +10]'),('GMT+11','[GMT +11]'),('GMT+12','[GMT +12]'),('GMT-11','[GMT -11]'),('GMT-10','[GMT -10]'),('GMT-9','[GMT -9]'),('GMT-8','[GMT -8]'),('GMT-7','[GMT -7]'),('GMT-6','[GMT -6]'),('GMT-5','[GMT -5]'),('GMT-4','[GMT -4]'),('GMT-3','[GMT -3]'),('GMT-2','[GMT -2]'),('GMT-1','[GMT -1]')], string='Time Zone')
	x_training_notes = fields.Text(string='Notes on Training')
	
	x_primary_cat = fields.Many2one(string='Primary CAT Tool', comodel_name='x_res.cat')
	x_other_cat = fields.Text(string='Other CAT Tools')
	
	x_rate_per_word = fields.Float(string='Rate Per Word')
	x_rate_info = fields.Text(string='Rate Information')

	# NOTE: Tony
	x_po_ids = fields.Many2many(comodel_name="account.invoice", string="Purchase Orders", compute="get_purchase_orders", readonly="true", copy=False)
	x_po_total_amount = fields.Monetary(string='Total amount of pos', compute="get_purchase_orders")
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)

	# _name = 'translationie_respartner_modifications.translationie_respartner_modifications'
	# name = fields.Char()

	@api.multi
	def get_purchase_orders(self):
		for partner in self:
			try:
				po_ids = self.env['account.invoice'].search([('partner_id','=', partner.id), ('type','=','in_invoice'), ('state', '!=', 'draft')])
				po_refund_ids = self.env['account.invoice'].browse()

				if po_ids:
					po_refund_ids = po_refund_ids.search([('type', '=', 'in_refund'), ('origin', 'in', po_ids.mapped('number')), ('origin', '!=', False)])

				total_po_amounts = sum([amount.amount_total for amount in po_ids])
				total_po_refund_amounts = sum([amount.amount_total for amount in po_refund_ids])

				partner.update({
					'x_po_total_amount': total_po_amounts + total_po_refund_amounts,
					'x_po_ids': po_ids + po_refund_ids
				})
			except Exception:
				_logger.debug("error getting pos" + str(total_po_amounts) + str(partner), exc_info=True)