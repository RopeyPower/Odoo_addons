# -*- encoding: utf-8 -*-
# 2018 Léo-Paul Géneau

import logging
import base64
import StringIO
import hashlib

import dateutil.parser
from openerp import _, exceptions, models, fields, api

try:
	import unicodecsv
except ImportError:
	pass

_logger = logging.getLogger(__name__)

class BankAccountStatementParser(models.TransientModel):
	_inherit = 'account.bank.statement.import'
	
	file_name = fields.Char("File Name")
	
	@api.multi
	def import_file(self):
		""" Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
		self.ensure_one()
		# Let the appropriate implementation module parse the file and return the required data
		# The active_id is passed in context in case an implementation module requires information about the wizard state (see QIF)
		currency_code, account_number, stmts_vals = self.with_context(active_id=self.ids[0])._parse_file(base64.b64decode(self.data_file))
		# Check raw data
		self._check_parsed_data(stmts_vals)
		_logger.debug("Finding Journal")
		# Try to find the currency and journal in odoo
		currency, journal = self._find_additional_data(currency_code, account_number)
		_logger.debug("Journal is: " + str(journal))
		# If no journal found, ask the user about creating one
		if not journal:
			# The active_id is passed in context so the wizard can call import_file again once the journal is created
			return self.with_context(active_id=self.ids[0])._journal_creation_wizard(currency, account_number)
		# Prepare statement data to be used for bank statements creation
		stmts_vals = self._complete_stmts_vals(stmts_vals, journal, account_number)
		# Create the bank statements
		statement_ids, notifications = self._create_bank_statements(stmts_vals)
		# Now that the import worked out, set it as the bank_statements_source of the journal
		journal.bank_statements_source = 'file_import'
		# Finally display the imported bank statement
		bank_statement_view_id = self.env.ref('bank_account_statement_parser.bank_statement_view').id
		
		return {
			'type': 'ir.actions.act_window',
			'name': 'Bank Statement Display',
			'view_type': 'form',
			'res_model': 'account.bank.statement',
			'res_id': statement_ids[0],
			'views': [(bank_statement_view_id, 'form')],
			'view_id': bank_statement_view_id,
		}

	def _check_csv(self, file):
		try:
			fieldnames = ['NSC', 'AC', 'Type', 'Currency', 'Date', 'X', 'Description', 'Debit', 'Credit', 'Balance']
			dict = unicodecsv.DictReader(file, fieldnames=fieldnames, delimiter=',', encoding='iso-8859-1')
		except:
			return False
		return dict
		
	def _bank_statement_init(self, csv):
		line1 = next(csv)
		currency_code = line1['Currency']
		account_number = self._get_account_number(line1['NSC'] + line1['AC'])
		
		bank_statement = {}
		bank_statement['name'] = self.file_name
		bank_statement['date'] = self._string_to_date(line1['Date'])
		bank_statement['balance_start'] = float(line1['Balance'])
		bank_statement['balance_end_real'] = bank_statement['balance_start']
		bank_statement['transactions'] = []
		
		return currency_code, account_number, bank_statement
		
	def _get_account_number(self, account_number):
		journal = self.env['account.journal'].browse(self.env.context.get('journal_id', []))
		_logger.debug("san acc: " + str(journal.bank_account_id.sanitized_acc_number[-14:]) + " acc: " + str(account_number))
		if journal.bank_account_id.sanitized_acc_number[-14:] == account_number:
			return journal.bank_account_id.sanitized_acc_number
		else:
			return account_number
	
	def _string_to_date(self, date_string):
		return dateutil.parser.parse(date_string, dayfirst=True, fuzzy=True).date()
		
	def _import_id(self, line):
		m = hashlib.sha512()
		m.update(str(line))
		m.hexdigest()
	
	def _parse_file(self, data_file):
		csv = self._check_csv(StringIO.StringIO(data_file))
		if not csv:
			return super(AccountBankStatementImport, self)._parse_file(data_file)
		bank_statements_data = []
		
		try:
			currency_code, account_number, bank_statement = self._bank_statement_init(csv)
			
			for line in csv:
				transaction = {}
				transaction['name'] = line['Description']
				transaction['date'] = self._string_to_date(line['Date'])
				transaction['amount'] = float(line['Debit'] + line['Credit'])
				transaction['unique_import_id'] = self._import_id(line)
				transaction['ref'] = bank_statement['name'] + '-' + line['Description']
				bank_statement['transactions'].append(transaction)
				bank_statement['balance_end_real'] += float(transaction['amount'])
			bank_statements_data.append(bank_statement)

		except Exception, e:
			_logger.debug("error parsing statement amount: " + str(csv), exc_info=True)
			raise exceptions.UserError(_(
				'The following problem occurred during import. The file might '
				'not be valid.\n\n %s' % e.message))
		return currency_code, account_number, bank_statements_data