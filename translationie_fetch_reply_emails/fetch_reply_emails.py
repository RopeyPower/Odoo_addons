# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
from openerp.exceptions import except_orm, Warning, UserError
from openerp import SUPERUSER_ID
from imaplib import IMAP4
from imaplib import IMAP4_SSL
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import email
from email.message import Message
from openerp.addons.mail.models.mail_message import decode
from openerp.tools.translate import _
import logging
import datetime
import dateutil
import xmlrpclib
import time
import smtplib



_logger = logging.getLogger(__name__)
MAIL_TIMEOUT = 180

class fetch_reply_emails(models.Model):
	_name = 'fetchreply.mailbox'
	
	name = fields.Char(string='Name')
	active = fields.Boolean(string='Active', default=True)
	state = fields.Selection([('draft','Not Confirmed'),('done','Confirmed')], string='Status', readonly=True, default='draft')
	imap_server = fields.Char(string='Incoming Server Name', help='Hostname or IP of the incoming mail server, must support IMAP.')
	imap_port = fields.Integer(string='Imap Port')
	imap_is_ssl = fields.Boolean(string='SSL/TLS', help='Connections are encrypted with SSL/TLS through a dedicated port (default: 993)')
	smtp_server = fields.Char(string='Outgoing Server Name', help='Hostname or IP of the outgoing mail server.')
	smtp_port = fields.Integer(string='Smtp Port')
	smtp_encryption = fields.Selection([('none','None'),('starttls','TLS (STARTTLS)'),('ssl','SSL/TLS')],string='Connection Security', required=True,help="Choose the connection encryption scheme:\n""- None: SMTP sessions are done in cleartext.\n""- TLS (STARTTLS): TLS encryption is requested at start of SMTP session (Recommended)\n""- SSL/TLS: SMTP sessions are encrypted with SSL/TLS through a dedicated port (default: 465)")
	date = fields.Datetime(string='Last Fetch Date', readonly=True)
	user = fields.Char(string='Username')
	password = fields.Char(string='Password')
	

	def onchange_imap_ssl(self, cr, uid, ids, ssl=False):
		port = 0
		values = {}
		port = ssl and 993 or 143
		values['imap_port'] = port
		
		return {'value':values}
		
	def onchange_smtp_encryption(self, cr, uid, ids, smtp_encryption):
		if smtp_encryption == 'ssl':
			result = {'value': {'smtp_port': 465}}
			if not 'SMTP_SSL' in smtplib.__all__:
				result['warning'] = {'title': _('Warning'),'message': _('Your server does not seem to support SSL, you may want to try STARTTLS instead')}
		else:
			result = {'value': {'smtp_port': 25}}
		return result

	def reset_draft(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {'state':'draft'})
		return True

	def connect_imap(self, cr, uid, server_id, context=None):
		if isinstance(server_id, (list,tuple)):
			server_id = server_id[0]
		server = self.browse(cr, uid, server_id, context)
		if server.imap_is_ssl:
			connection = IMAP4_SSL(server.imap_server, int(server.imap_port))
		else:
			connection = IMAP4(server.imap_server, int(server.imap_port))
		connection.login(server.user, server.password)
		connection.sock.settimeout(MAIL_TIMEOUT)
		return connection
	
	def connect_smtp(self, host, port, user=None, password=None, encryption=False, smtp_debug=False):
		#copied from ir.mail_server connect method
		if encryption == 'ssl':
			if not 'SMTP_SSL' in smtplib.__all__:
				raise UserError(_("Your OpenERP Server does not support SMTP-over-SSL. You could use STARTTLS instead."
									"If SSL is needed, an upgrade to Python 2.6 on the server-side should do the trick."))
			connection = smtplib.SMTP_SSL(host, port)
		else:
			connection = smtplib.SMTP(host, port)
		connection.set_debuglevel(smtp_debug)
		if encryption == 'starttls':
			# starttls() will perform ehlo() if needed first
			# and will discard the previous list of services
			# after successfully performing STARTTLS command,
			# (as per RFC 3207) so for example any AUTH
			# capability that appears only on encrypted channels
			# will be correctly detected for next step
			connection.starttls()

		if user:
			# Attempt authentication - will raise if AUTH service not supported
			# The user/password must be converted to bytestrings in order to be usable for
			# certain hashing schemes, like HMAC.
			# See also bug #597143 and python issue #5285
			user = tools.ustr(user).encode('utf-8')
			password = tools.ustr(password).encode('utf-8') 
			connection.login(user, password)
		return connection
	
	def button_test_imap_login(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for server in self.browse(cr, uid, ids, context=context):
			try:
				connection = server.connect_imap(server.id)
				server.write({'state':'done'})
			except Exception, e:
				_logger.exception("Failed to connect to IMAP server %s.", server.name)
				raise UserError("Connection test failed! \nHere is what we got instead:\n %s." % tools.ustr(e))
			#finally:
				#if connection:
					#connection.logout()
		return True
	
	def button_test_smtp_login(self, cr, uid, ids, context=None):
		for smtp_server in self.browse(cr, uid, ids, context=context):
			smtp = False
			try:
				smtp = self.connect_smtp(smtp_server.smtp_server, smtp_server.smtp_port, user=smtp_server.user,
									password=smtp_server.password, encryption=smtp_server.smtp_encryption)
			except Exception, e:
				raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s") % tools.ustr(e))
			finally:
				try:
					if smtp: smtp.quit()
				except Exception:
					# ignored, just a consequence of the previous exception
					pass
		raise UserError(_("Connection Test Succeeded! Everything seems properly set up!"))
	
	def _get_replies(self, cr, uid, ids=False, context=None):
		if not ids:
			ids = self.search(cr, uid, [('state','=','done')])
		return self.get_reply_emails(cr, uid, ids, context=context)
		
	def get_reply_emails(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		msg_obj = self.pool['mail.message']
		#test_msg_id = '<1459935698.697000026702881.190572240077960-openerp-840-sale.order@DevPc>'
		#test_mail = msg_obj.search(cr, uid, [('message_id','=',test_msg_id)])
		#test_email = self.pool['mail.message'].browse(cr, uid, test_mail[0])
		discussion_subtype = self.pool['mail.message.subtype'].search(cr, uid, [('name','=','Discussions')], context=context)
		all_email_ids = msg_obj.search(cr, uid, ['|','&',('message_type','=','comment'),('subtype_id','in',discussion_subtype),('message_type','=','email')], context=context)
		all_emails = msg_obj.browse(cr, uid, all_email_ids, context=context)
		_logger.debug("Number of messages: " + str(len(all_emails)))
		#emails = [test_email]
		for server in self.browse(cr, uid, ids, context=context):
			counter = 0;
			count, failed = 0, 0
			server_name = server.imap_server
			server_port = server.imap_port
			user = server.user
			password = server.password
			m_id = ''
			s_res = ''
			s_data = ''
			try:
				counter += 1
				imap_server = server.connect_imap(server.id)
				#imap_server.login(user, password)
				imap_server.select()
				for mail in all_emails:
					searchParam = '(Header in-reply-to "' + str(mail.message_id) + '")'
					m_id = mail.message_id
					result, data = imap_server.search(None, searchParam)
					s_res = str(result)
					s_data = str(data)
					for num in data[0].split():
						result, data = imap_server.fetch(num, '(RFC822)')
						msg = data[0][1]
						if isinstance(mail, bytearray):
							msg = str(msg.data)
						if isinstance(msg, xmlrpclib.Binary):
							msg = str(msg.data)
						if isinstance(msg, unicode):
							msg = msg.encode('utf-8')
						reply_txt = email.message_from_string(msg)
						try:
							reply_id = self.process_reply(cr, uid, reply_txt, mail, context=context)
						except Exception:
							_logger.exception('Failed to process reply from mailbox %s. date header is: %s', server_name, reply_txt.get('Date'))
							failed += 1
						count += 1
				_logger.info("Fetched %d reply(s) on IMAP mailbox %s; %d succeeded, %d failed.", count,  server_name, (count - failed), failed)
			except Exception:
				_logger.exception("General failure when trying to fetch reply from mailbox %s. for message %s result was %s data was %s email no %s search query %s", server_name, m_id, s_res, s_data, counter, searchParam)
			finally:
				imap_server.close()
				imap_server.logout()
			
			
	
	def process_reply(self ,cr, uid, reply, parent_msg, context=None):
		if context is None:
			context = {}
		reply_dict = self.parse_reply(cr, uid, reply, context=context)
		
		if reply_dict.get('message_id'):
			existing_msg_ids = self.pool['mail.message'].search(cr, SUPERUSER_ID, [('message_id', '=', reply_dict.get('message_id'))], context=context)
			
			if existing_msg_ids:
				#self.pool['mail.message'].unlink(cr, uid, reply_dict, context=context)
				#reply_msg = self.pool['mail.message'].search(cr, uid, [('id','=',reply_dict)], context=context)
				_logger.debug("reply is " + str(reply_dict))
				_logger.info('Ignored reply from %s to %s with Message-Id %s: found duplicated Message-Id during processing', reply_dict.get('from'), reply_dict.get('to'), reply_dict.get('message_id'))
				return
		self.route_reply(cr, uid, reply_dict, parent_msg, context=context)
		
		
	
	def route_reply(self, cr, uid, reply_dict, parent_msg, context=None):
		if context is None:
			context = {}
		reply_model = self.pool[parent_msg.model]
		reply_document = reply_model.browse(cr, uid, parent_msg.res_id, context=context)
		
		
		if reply_dict['message_id'] not in reply_document.message_ids:
			reply = self.pool['mail.message'].create(cr, uid, {'message_id':reply_dict['message_id'],'model':parent_msg.model,'res_id':parent_msg.res_id,'date':reply_dict['date'],'subject':reply_dict['subject'],'parent_id':parent_msg.id,'body':reply_dict['body'],'email_from':reply_dict['from'],'partner_ids':reply_dict['partner_ids'],'message_type':reply_dict['message_type'],'reply_to':reply_dict['from']},context=context)
			reply_document.write({'message_ids':[(4,reply)]})
			
	
	def parse_reply(self, cr, uid, message, context=None):
		msg_dict = {
			'message_type':'email',
		}
		if not isinstance(message, Message):
			message = message.encode('utf-8')
			message = email.message_from_string(message)
		
		message_id = message['message-id']
		if not message_id:
			message_id = "<%s@localhost>" % time.time()
			_logger.debug('Parsing Message without message_id, generating a random one: %s', message_id)
		msg_dict['message_id'] = message_id
		
		if message.get('Subject'):
			msg_dict['subject'] = decode(message.get('Subject'))
		
		msg_dict['from'] = message.get('from')
		msg_dict['to'] = message.get('to')
		msg_dict['cc'] = message.get('cc')
		email_addresses = [message['to'],message['cc']]
		partner_ids = self.get_partner_list(cr, uid, email_addresses, context=context)
		msg_dict['partner_ids'] = [(4, partner_id) for partner_id in partner_ids]
		
		if message.get('Date'):
			_logger.info('Date header is: ', message.get('Date'))
			try:
				date_hdr = decode(message.get('Date'))
				parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
				if parsed_date.utcoffset() is None:
					# naive datetime, so we arbitrarily decide to make it
					# UTC, there's no better choice. Should not happen,
					# as RFC2822 requires timezone offset in Date headers.
					stored_date = parsed_date.replace(tzinfo=pytz.utc)
				else:
					stored_date = parsed_date.astimezone(tz=pytz.utc)
			except Exception:
				_logger.warning('Failed to parse Date header %r in incoming mail '
								'with message-id %r, assuming current date/time.',
								message.get('Date'), message_id)
				stored_date = datetime.datetime.now()
			msg_dict['date'] = stored_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
		
		msg_dict['body'] = self.get_email_body(message)
		_logger.info('Date header is: ', message.get('Date'))
		return msg_dict
	
	
	def get_partner_list(self, cr, uid, email_addresses, context=None):
		#get partners_id's for email addresses
		partner_obj = self.pool['res.partner']
		partner_ids = []
		for email_address in email_addresses:
			partner_id = partner_obj.search(cr, SUPERUSER_ID,[('email','ilike',email_address)],limit=1, context=context)
			if partner_id:
				partner_id = partner_id[0]
				partner_ids.append(partner_id)
		return partner_ids
		
	def get_email_body(self, message):
		body = u''
		
		if not message.is_multipart() or message.get('content-type','').startswith("text/"):
			encoding = message.get_content_charset()
			body = message.get_payload(decode=True)
			body = tools.ustr(body, encoding, errors='replace')
			if message.get_content_type() == 'text/plain':
				body = tools.append_content_to_html(u'', body, preserve=True)
		else:
			alternative = False
			mixed = False
			html = u''
			for part in message.walk():
				if part.get_content_type() == 'multipart/alternative':
					alternative = True
				if part.get_content_type() == 'multipart/mixed':
					mixed = True
				if part.get_content_maintype() == 'multipart':
					continue
				
				encoding = part.get_content_charset()
				if part.get_content_type() == 'text/plain' and (not alternative or not body):
					body = tools.append_content_to_html(body, tools.ustr(part.get_payload(decode=True), encoding, errors='replace'), preserve=True)
				elif part.get_content_type() == 'text/html':
					append_content = not alternative or (html and mixed)
					html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
					if not append_content:
						body = html
					else:
						body = tools.append_content_to_html(body, html, plaintext=False)
		return body
		
	def upload_email_to_sent_folder(self, server, message):
		imap_server = server.connect_imap(server.id)
		try:
			typ, data = imap_server.append('Sent Items',None,None,str(message))
			_logger.debug("type : " + str(typ) + " data " + str(data))
		except:
			_logger.debug("error uploading email ", exc_info=True)
		finally:
			imap_server.logout()
		