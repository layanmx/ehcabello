# Copyright 2018 Vauxoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def _l10n_mx_edi_retry(self):
        """avoid generating cfdi when the cfdi was attached"""
        if self._context.get('resign_cfdi', True):
            return super(AccountPayment, self)._l10n_mx_edi_retry()
        to_retry_payments = self.filtered(
            lambda pay: pay.l10n_mx_edi_pac_status != 'signed')
        return super(AccountPayment, to_retry_payments)._l10n_mx_edi_retry()
