# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2021. All rights reserved.


import json
import logging
from urllib.parse import urljoin

import requests
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AcquirerMyFatoora(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('myfatoora', 'MyFatoora')], ondelete={'myfatoora': 'set default'})
    token = fields.Char('Token', groups='base.group_user')
    payment_url = fields.Char(string="Payment URL")

    @api.model
    def _get_authorize_urls(self):
        base_url = self.get_base_url()
        """ MyFatoora URLS """
        return base_url + 'shop/myfatoora/payment/'

    def _get_feature_support(self):
        res = super(AcquirerMyFatoora, self)._get_feature_support()
        res['fees'].append('myfatoora')
        return res

    @api.model
    def _get_myfatoora_urls(self):
        # var = self.execute_payment()

        # print("var", var['Data']['PaymentURL'])
        base_url = self.get_base_url()
        """ MyFatoora URLS """
        # if environment == 'prod':
        #     return {
        #         'myfatoora_form_url': base_url + "shop/myfatoora/payment/",
        #     }
        # else:

        return {
            'myfatoora_form_url': base_url + "shop/myfatoora/payment/"
        }

    def myfatoora_form_generate_values(self, values):
        currency = self.env['res.currency'].browse(values['currency_id'])
        partner = self.env['res.partner'].browse(values.get('partner_id'))
        base_url = self.get_base_url()
        myfatoora_tx_values = dict(values)
        _logger.info(values.get('amount'))
        myfatoora_tx_values.update({
            "InvoiceValue": values.get('amount'),
            "PaymentMethodId": 2,
            "CustomerName": partner.name,
            "CustomerBlock": "",
            "CustomerStreet": partner.street,
            "CustomerHouseBuildingNo": "",
            "CustomerCivilId": "",
            "CustomerAddress": values.get('partner_address'),
            "CustomerReference": values.get('reference'),
            "CountryCodeId": partner.country_id.code,
            "CustomerMobile": partner.phone,
            "CustomerEmail": partner.email,
            "DisplayCurrencyId": currency.name,
            "SendInvoiceOption": 1,
            "CallBackUrl": self.get_base_url(),
            "ErrorUrl": self.get_base_url(),
            'return_url': '%s' % urljoin(base_url, '/payment/myfatoora/return'),
            "Language": 1,
            "SourceInfo": "",
            "Environment": self.state
        })

        return myfatoora_tx_values

    #
    def myfatoora_get_form_action_url(self):
        # self.initiate_payment()
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_myfatoora_urls(environment)['myfatoora_form_url']

    def initiate_payment(self, state=False):
        if state:
            baseURL = "https://apitest.myfatoorah.com" if state == 'test' else "https://api.myfatoorah.com"
        else:
            baseURL = "https://apitest.myfatoorah.com"
        provider = self.env['payment.acquirer'].sudo().search([('provider', '=', 'myfatoora')])
        token = provider.sudo().token
        url = baseURL + "/v2/InitiatePayment"
        payload = {
            "InvoiceAmount": 1,
            "CurrencyIso": self.env.company.currency_id.name
        }
        try:
            headers = {'Content-Type': "application/json", 'Authorization': "bearer " + token}
            response = requests.request("POST", url, data=str(payload), headers=headers)
        except UserError as e:
            raise UserError(_(e))
        if response:
            return json.loads(response.text)
        else:
            return None

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'myfatoora':
            return super()._get_default_payment_method_id()
        # return self.env.ref('payment_hyperpay.payment_method_hyperpay').id
        return self.env.ref('payment_myfatoora.payment_method_myfatoorah').id

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)
        return super(AcquirerMyFatoora, self)._get_compatible_acquirers(*args, currency_id=None, **kwargs)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'myfatoora':
            return res

        base_url = self.acquirer_id.get_base_url()
        rendering_values = self.acquirer_id.myfatoora_form_generate_values(processing_values)
        rendering_values.update({
            'api_url': self.acquirer_id._get_authorize_urls(),
        })
        return rendering_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):

        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'myfatoora':
            return tx

        _logger.info(data)
        transaction_id = 1
        for transaction in data['Data']['InvoiceTransactions']:
            transaction_id = transaction['TransactionId']
        reference, txn_id = data['Data']['CustomerReference'], transaction_id
        if not reference or not txn_id:
            error_msg = _('MyFatoorah: received data with missing reference (%s) or (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'MyFatoorah: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    def _myfatoora_form_get_invalid_parameters(self, data):
        transaction_id = 1
        for transaction in data['Data']['InvoiceTransactions']:
            transaction_id = transaction['TransactionId']
        invalid_parameters = []
        if self.acquirer_reference and transaction_id != self.acquirer_reference:
            invalid_parameters.append(('TransactionId', transaction_id, self.acquirer_reference))
        return invalid_parameters

    def _process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != 'myfatoora':
            return
        transaction_status = ''
        transaction_id = 1
        for transaction in data['Data']['InvoiceTransactions']:
            transaction_status = transaction['TransactionStatus']
            transaction_id = transaction['TransactionId']
        if transaction_status == 'Succss':
            success_message = "Transaction Successfully Completed"
            logger_msg = _('MyFatoorah:' + success_message)
            _logger.info(logger_msg)
            self.write({
                'acquirer_reference': transaction_id,
            })
            self._set_done()
        elif transaction_status == 'InProgress':
            pending_message = "Transaction is Pending"
            logger_msg = _('MyFatoorah:' + pending_message)
            _logger.info(logger_msg)
            self.write({
                'acquirer_reference': transaction_id,
            })
            self._set_pending()
        elif transaction_status == 'Failed':
            error_message = "Transaction Failed!!"
            error = _('MyFatoorah:' + error_message)
            _logger.info(error)
            self.write({'state_message': error})
            self._set_canceled()


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['myfatoora'] = {'mode': 'unique', 'domain': [('type', '=', 'bank')]}
        return res
