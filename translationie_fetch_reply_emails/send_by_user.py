# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
from openerp.exceptions import except_orm, Warning
from openerp import SUPERUSER_ID
from openerp.addons.base.ir.ir_mail_server import try_coerce_ascii, extract_rfc2822_addresses, encode_header, encode_header_param, encode_rfc2822_address_header, MailDeliveryException, WriteToLogger
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.charset import Charset
from email.header import Header
from email.utils import formatdate, make_msgid, COMMASPACE, getaddresses, formataddr
from email import Encoders
from openerp.tools.translate import _
import logging
import re
import smtplib
import threading

# ustr was originally from tools.misc.
# it is moved to loglevels until we refactor tools.
from openerp.loglevels import ustr

_logger = logging.getLogger(__name__)

class send_by_user(models.Model):
	_inherit = 'ir.mail_server'
	
	def send_email(self, cr, uid, message, mail_server_id=None, smtp_server=None, smtp_port=None,
				   smtp_user=None, smtp_password=None, smtp_encryption=None, smtp_debug=False,
				   context=None):
		"""Sends an email directly (no queuing).

		No retries are done, the caller should handle MailDeliveryException in order to ensure that
		the mail is never lost.

		If the mail_server_id is provided, sends using this mail server, ignoring other smtp_* arguments.
		If mail_server_id is None and smtp_server is None, use the default mail server (highest priority).
		If mail_server_id is None and smtp_server is not None, use the provided smtp_* arguments.
		If both mail_server_id and smtp_server are None, look for an 'smtp_server' value in server config,
		and fails if not found.

		:param message: the email.message.Message to send. The envelope sender will be extracted from the
						``Return-Path`` (if present), or will be set to the default bounce address.
						The envelope recipients will be extracted from the combined list of ``To``,
						``CC`` and ``BCC`` headers.
		:param mail_server_id: optional id of ir.mail_server to use for sending. overrides other smtp_* arguments.
		:param smtp_server: optional hostname of SMTP server to use
		:param smtp_encryption: optional TLS mode, one of 'none', 'starttls' or 'ssl' (see ir.mail_server fields for explanation)
		:param smtp_port: optional SMTP port, if mail_server_id is not passed
		:param smtp_user: optional SMTP user, if mail_server_id is not passed
		:param smtp_password: optional SMTP password to use, if mail_server_id is not passed
		:param smtp_debug: optional SMTP debug flag, if mail_server_id is not passed
		:return: the Message-ID of the message that was just sent, if successfully sent, otherwise raises
				 MailDeliveryException and logs root cause.
		"""
		# Use the default bounce address **only if** no Return-Path was
		# provided by caller.  Caller may be using Variable Envelope Return
		# Path (VERP) to detect no-longer valid email addresses.
		smtp_from = message['Return-Path']
		if not smtp_from:
			smtp_from = self._get_default_bounce_address(cr, uid, context=context)
		if not smtp_from:
			smtp_from = message['From']
		assert smtp_from, "The Return-Path or From header is required for any outbound email"

		# The email's "Envelope From" (Return-Path), and all recipient addresses must only contain ASCII characters.
		from_rfc2822 = extract_rfc2822_addresses(smtp_from)
		assert from_rfc2822, ("Malformed 'Return-Path' or 'From' address: %r - "
							  "It should contain one valid plain ASCII email") % smtp_from
		# use last extracted email, to support rarities like 'Support@MyComp <support@mycompany.com>'
		smtp_from = from_rfc2822[-1]
		email_to = message['To']
		email_cc = message['Cc']
		email_bcc = message['Bcc']
		
		smtp_to_list = filter(None, tools.flatten(map(extract_rfc2822_addresses,[email_to, email_cc, email_bcc])))
		assert smtp_to_list, self.NO_VALID_RECIPIENT

		x_forge_to = message['X-Forge-To']
		if x_forge_to:
			# `To:` header forged, e.g. for posting on mail.groups, to avoid confusion
			del message['X-Forge-To']
			del message['To'] # avoid multiple To: headers!
			message['To'] = x_forge_to

		# Do not actually send emails in testing mode!
		if getattr(threading.currentThread(), 'testing', False):
			_test_logger.info("skip sending email in test mode")
			return message['Message-Id']

		# Get SMTP Server Details from Mail Server
		mail_server = None
		if mail_server_id:
			mail_server = self.browse(cr, SUPERUSER_ID, mail_server_id)
		elif not smtp_server:
			mail_server_ids = self.search(cr, SUPERUSER_ID, [], order='sequence', limit=1)
			if mail_server_ids:
				mail_server = self.browse(cr, SUPERUSER_ID, mail_server_ids[0])

		# Look up if sender has own mailbox, if so send with that as the mail server
		user_mailbox = self.pool['fetchreply.mailbox'].search(cr,uid,[('user','ilike',smtp_from)])
		_logger.debug("smtp_from: " + smtp_from + " user " + str(user_mailbox))
		
		if user_mailbox:
			user_mailbox = self.pool['fetchreply.mailbox'].browse(cr,uid,user_mailbox[0],context=context)
			user_mailbox = user_mailbox[0]
			smtp_server = user_mailbox.smtp_server
			smtp_user = user_mailbox.user
			smtp_password = user_mailbox.password
			smtp_port = user_mailbox.smtp_port
			smtp_encryption = user_mailbox.smtp_encryption
			smtp_debug = smtp_debug
			
			user_mailbox.upload_email_to_sent_folder(user_mailbox, message)
		elif mail_server:
			smtp_server = mail_server.smtp_host
			smtp_user = mail_server.smtp_user
			smtp_password = mail_server.smtp_pass
			smtp_port = mail_server.smtp_port
			smtp_encryption = mail_server.smtp_encryption
			smtp_debug = smtp_debug or mail_server.smtp_debug
		else:
			# we were passed an explicit smtp_server or nothing at all
			smtp_server = smtp_server or tools.config.get('smtp_server')
			smtp_port = tools.config.get('smtp_port', 25) if smtp_port is None else smtp_port
			smtp_user = smtp_user or tools.config.get('smtp_user')
			smtp_password = smtp_password or tools.config.get('smtp_password')
			if smtp_encryption is None and tools.config.get('smtp_ssl'):
				smtp_encryption = 'starttls' # STARTTLS is the new meaning of the smtp_ssl flag as of v7.0
		
		_logger.debug("sending mail from mailbox: " + smtp_user)
		if not smtp_server:
			raise UserError(_("Missing SMTP Server")+ "\n" + _("Please define at least one SMTP server, or provide the SMTP parameters explicitly."))

		try:
			message_id = message['Message-Id']

			# Add email in Maildir if smtp_server contains maildir.
			if smtp_server.startswith('maildir:/'):
				from mailbox import Maildir
				maildir_path = smtp_server[8:]
				mdir = Maildir(maildir_path, factory=None, create = True)
				mdir.add(message.as_string(True))
				return message_id

			smtp = None
			try:
				smtp = self.connect(smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption or False, smtp_debug)
				smtp.sendmail(smtp_from, smtp_to_list, message.as_string())
			finally:
				if smtp is not None:
					smtp.quit()
		except Exception, e:
			msg = _("Mail delivery failed via SMTP server '%s'.\n%s: %s") % (tools.ustr(smtp_server),
																			 e.__class__.__name__,
																			 tools.ustr(e))
			_logger.error(msg)
			raise MailDeliveryException(_("Mail Delivery Failed"), msg)
		return message_id