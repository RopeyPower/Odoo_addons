# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import UserError
from lxml import etree
import logging

_logger = logging.getLogger(__name__)



class PartnerBankMod(models.Model):
	_inherit = 'res.partner.bank'
	
	x_account_payee = fields.Char(string='Payee Name', help='Payee name to appear on SEPA payments instead of Account holder name')

class AccountPaymentOrder(models.Model):
	_inherit = 'account.payment.order'
	
	@api.model
	def generate_party_block(
			self, parent_node, party_type, order, partner_bank, gen_args,
			bank_line=None):
		"""Generate the piece of the XML file corresponding to Name+IBAN+BIC
		This code is mutualized between TRF and DD
		In some localization (l10n_ch_sepa for example), they need the
		bank_line argument"""
		assert order in ('B', 'C'), "Order can be 'B' or 'C'"
		if party_type == 'Cdtr':
			party_type_label = 'Creditor'
		elif party_type == 'Dbtr':
			party_type_label = 'Debtor'
		if partner_bank.x_account_payee:
			name = 'partner_bank.x_account_payee'
		else:
			name = 'partner_bank.partner_id.name'
		
		_logger.debug("party_name should be " + str(name) + " bank " + str(partner_bank) + " order " + str(order))
		eval_ctx = {'partner_bank': partner_bank}
		party_name = self._prepare_field(
			'%s Name' % party_type_label, name, eval_ctx,
			gen_args.get('name_maxsize'), gen_args=gen_args)
		# At C level, the order is : BIC, Name, IBAN
		# At B level, the order is : Name, IBAN, BIC
		if order == 'C':
			self.generate_party_agent(
				parent_node, party_type, order, partner_bank, gen_args,
				bank_line=bank_line)
		party = etree.SubElement(parent_node, party_type)
		party_nm = etree.SubElement(party, 'Nm')
		party_nm.text = party_name
		partner = partner_bank.partner_id
		if partner.country_id:
			postal_address = etree.SubElement(party, 'PstlAdr')
			country = etree.SubElement(postal_address, 'Ctry')
			country.text = self._prepare_field(
				'Country', 'partner.country_id.code',
				{'partner': partner}, 2, gen_args=gen_args)
			if partner.street:
				adrline1 = etree.SubElement(postal_address, 'AdrLine')
				adrline1.text = self._prepare_field(
					'Adress Line1', 'partner.street',
					{'partner': partner}, 70, gen_args=gen_args)
			if partner.city and partner.zip:
				adrline2 = etree.SubElement(postal_address, 'AdrLine')
				adrline2.text = self._prepare_field(
					'Address Line2', "partner.zip + ' ' + partner.city",
					{'partner': partner}, 70, gen_args=gen_args)

		self.generate_party_acc_number(
			parent_node, party_type, order, partner_bank, gen_args,
			bank_line=bank_line)

		if order == 'B':
			self.generate_party_agent(
				parent_node, party_type, order, partner_bank, gen_args,
				bank_line=bank_line)
		return True