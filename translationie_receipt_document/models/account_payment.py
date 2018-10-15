from openerp import models, fields, api, _
import svgwrite
from wand.image import Image
import unicodedata
import logging

_logger = logging.getLogger(__name__)

class account_payment(models.Model):
	_inherit = 'account.payment'
	
	receipt_svg = fields.Text()
	
	@api.multi
	def post(self):
		try:
			_logger.debug("IN NEW POST")
			super(account_payment, self).post()
			_logger.debug("Finished Posting Payment")
			self.create_receipt()
		except Exception:
			_logger.error("ERROR POSTING PAYMENT", exc_info=True)
	
	def _format_order_ref(self, order_ref):
		order_ref_lines = []
		if len(order_ref) > 43:
			order_ref_chunks = order_ref.split(',')
			line = ''
			_logger.debug("Ref Chunks: " + str(order_ref_chunks))
			for i, chunk in enumerate(order_ref_chunks):
				_logger.debug("Iteration: " + str(i) + " of " + str(len(order_ref_chunks)))
				_logger.debug("Current Chunk: " + chunk)
				line_length = len(line)
				new_length = line_length + len(chunk) + 1
				if line_length < 43 and new_length <= 43:
					line += chunk + ','
					_logger.debug("Line: " + line + " Length: " + str(line_length) + " new length: " + str(new_length))
				else:
					order_ref_lines.append(line)
					line = chunk
					if i == len(order_ref_chunks) - 2:
						order_ref_lines.append(line)
			# _logger.debug("Chunk 1: " + str(order_ref_chunks[0:2]) + " Chunk2: " + str(order_ref_chunks[1::2]) + " chunk3: " + str(order_ref_chunks[2::3]))
			# order_ref_lines = [x + ', ' + y for x,y in zip(order_ref_chunks[0:3], order_ref_chunks[1::3], order_ref_chunks[2::3])]
		else:
			order_ref_lines.append(order_ref)
		return order_ref_lines
	
	@api.multi
	def create_receipt(self):
		try:
			_logger.debug("Creating Receipt")
			for rec in self:
				if not rec.receipt_svg:
					_logger.debug("creating receipt")
					# sale_order = self.env['sale.order'].search([('name','=',invoice.origin)])
					# _logger.debug("Receipt Sale Order: " + str(sale_order))
					receipt_name = rec.partner_id.name + "_" + rec.name + "_Receipt.png"
					order_ref = ''
					for invoice in rec.invoice_ids:
						if invoice.origin:
							order_ref += invoice.origin + ', '
						else:
							order_ref += invoice.number + ','
						
					order_ref_lines = self._format_order_ref(order_ref)
						
					_logger.debug("ref lines: " + str(order_ref_lines))
					
					receipt = svgwrite.Drawing(filename=receipt_name, size=("464px", "501px"))
					
					receipt.add(receipt.rect(insert=('4%','4%'),
								size=("98%","98%"),
								stroke_width="2",
								stroke="black",
								fill = "rgb(255,255,255)"))
					normal_size = "font-size:14pt;font-weight:normal;"
					y = 12
					receipt.add(receipt.text("RECEIPT", insert=('50%',str(y) + '%'), text_anchor="middle", style="font-size:32px;font-weight:bold;"))
					#15%
					y += 6
					receipt.add(receipt.text(str(rec.company_id.name), insert=('50%',str(y) + '%'), text_anchor="middle", style=normal_size))
					# order_ref = 'REF: ' + order_ref
					y += 6
					receipt.add(receipt.text("ORDER REFERENCE:", insert=('50%',str(y) + '%'), text_anchor="middle", style="font-size:16pt;font-weight:bold;"))
					for line in order_ref_lines:
						y += 6
						receipt.add(receipt.text(line, insert=('50%',str(y) + '%'), text_anchor="middle", style="font-size:16pt;font-weight:bold;"))
					y += 3
					receipt.add(receipt.line(start=('15%',str(y) +'%'),end=('85%',str(y) + '%'), stroke_width="1", stroke="black"))
					y += 6
					receipt.add(receipt.text("SALE TRANSACTION", insert=('50%',str(y) + '%'), text_anchor="middle", style=normal_size))
					y += 7
					amount_line = str(rec.amount) + ' ' + str(rec.currency_id.name)
					receipt.add(receipt.text(amount_line, insert=('50%',str(y) + '%'), text_anchor="middle", style="font-size:20pt;font-weight:bold;"))
					y += 6
					receipt.add(receipt.text(str(rec.payment_date), insert=('50%',str(y) + '%'), text_anchor="middle", style=normal_size))
					y += 4
					receipt.add(receipt.line(start=('15%',str(y) + '%'),end=('85%',str(y) + '%'), stroke_width="1", stroke="black"))
					y += 5
					customer_name = unicodedata.normalize('NFKD', rec.partner_id.name).encode('ascii','ignore')
					receipt.add(receipt.text(customer_name, insert=('50%',str(y) + '%'), text_anchor="middle", style=normal_size))
					y += 4
					#56%
					receipt.add(receipt.rect(insert=('15%',str(y) +'%'), size=('70%','20%'), fill="green"))
					y += 6
					#62%
					receipt.add(receipt.text("Paid By:", insert=('50%',str(y) + '%'), text_anchor="middle", fill="white", style=normal_size))
					payment_desc = []
					if "Bank" in rec.journal_id.name:
						payment_desc.append("Bank Transfer to")
						payment_desc.append(str(rec.journal_id.bank_account_id.acc_number))
					else:
						payment_desc.append(str(rec.journal_id.name))
					y += 5
					#74%
					for line in payment_desc:
						y_pos = str(y) + '%'
						receipt.add(receipt.text(line, insert=('50%',y_pos), text_anchor="middle", fill="white", style=normal_size))
						y += 5
					
					with Image(blob=receipt.tostring().encode('ascii'), format="svg") as image:
						png_image = image.make_blob("png")
					_logger.debug("SVG IMAGE: " + receipt.tostring())
					_logger.debug("Payment Record: " + str(rec))
					
					attachment = self.env['ir.attachment'].create({
							'res_model': 'account.payment',
							'res_id': rec.id,
							'name': receipt_name,
							'datas': png_image.encode('base64'),
							'datas_fname': receipt_name,
							})
					rec.receipt_svg = receipt.tostring()
					self.attach_to_sale_orders(rec.invoice_ids, receipt_name, png_image)
					
				
		except Exception:
			_logger.error("REceipt Error", exc_info=True)
			
	def attach_to_sale_orders(self, invoice_ids, receipt_name, image):
		sale_orders = False
		for invoice in invoice_ids:
			so_list = [s.strip() for s in str(invoice.origin).split(',')]
			_logger.debug("Invoice List: " + str(so_list))
			# so_names = invoice.origin.split(',')
			sale_orders = self.env['sale.order'].search([('name','in',so_list)])
			_logger.debug("SOS: " + str(sale_orders));
		for so in sale_orders:
			attachment = self.env['ir.attachment'].create({
				'res_model': 'sale.order',
				'res_id': so.id,
				'name': receipt_name,
				'datas': image.encode('base64'),
				'datas_fname': receipt_name,
				})
			#check attachments
			receipt_attach = self.env['ir.attachment'].search([('res_id','=',so.id),('res_model','=','sale.order'),('name','ilike','Receipt.png')]).ids
			_logger.debug("documents: " + str(receipt_attach))
			
			
	@api.multi
	def cancel(self):
		try:
			super(account_payment, self).cancel()
			for rec in self:
				attachment_obj = self.env['ir.attachment']
				attachments = attachment_obj.search([('res_id','=',rec.id),('res_model','=','account.payment')])
				_logger.debug("documents: " + str(attachments))
				for attachment in attachments:
						_logger.debug("atatchment name: " + str(attachment.name))
						so_attachments = attachment_obj.search([('name','=',attachment.name),('res_model','=','sale.order')])
						_logger.debug("so attachments: " + str(so_attachments))
						so_attachments.unlink()
				attachments.unlink()
				rec.receipt_svg = False
		except Exception:
			_logger.error("error cancelling payment", exc_info=True)
		
		
	# @api.multi
	# def unlink(self):
		# try:
			# if any(rec.state != 'draft' for rec in self):
				# raise UserError(_("You can not delete a payment that is already posted"))
			# for rec in self:
				# attachment_obj = self.env['ir.attachment']
				# attachments = attachment_obj.search([('res_id','=',rec.id),('res_model','=','account.payment')])
				# _logger.debug("documents: " + str(attachments))
				# for attachment in attachments:
						# _logger.debug("atatchment name: " + str(attachment.name))
						# so_attachments = attachment_obj.search([('name','=',attachment.name),('res_model','=','sale.order')])
						# _logger.debug("so attachments: " + str(so_attachments))
						# so_attachments.unlink()
			# result = super(account_payment, self).unlink()
			# return result
		# except Exception:
			# _logger.error("error deleting payment", exc_info=True)


# class account_register_payments(models.TransientModel):
	# _inherit = 'account.register.payments'
	
	# @api.multi
	# def create_payment(self):
		# action = super(account_register_payments, self).create_payment()
		# invoices = self._get_invoices()
		# for invoice in invoices:
			# if invoice.reconciled:
				# self.create_receipt(invoice)
		# return action
		
