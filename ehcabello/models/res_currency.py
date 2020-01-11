# Copyright 2018 Vauxoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.addons import decimal_precision as dp


class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    rate = fields.Float(digits=dp.get_precision('Rate Precision'))
