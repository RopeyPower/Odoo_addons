from openerp import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
	_inherit = "sale.order"
	
	x_receipt_attachments = fields.Many2many(comodel_name='ir.attachment', compute="_compute_receipt_attachments")
	
	@api.depends('invoice_ids.residual')
	def _compute_receipt_attachments(self):
		# get valid receipt attachments
		# valid attachment is one attached to a payment that is for an invoice belonging to this sale order
		if self.invoice_status != 'no':
			_logger.debug("Finding Attachments")
			payment_ids = []
			for invoice in self.invoice_ids:
				for payment in invoice.payment_ids:
					if payment.receipt_svg:
						payment_ids.append(payment.id)
			if len(payment_ids) > 0:
				attachment_ids = self.env['ir.attachment'].search([('res_id','in',payment_ids),('res_model','=','account.payment')])
				_logger.debug("Attachments: " + str(attachment_ids.ids))
				self.x_receipt_attachments = [(6, 0, attachment_ids.ids)]
		
	