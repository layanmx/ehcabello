# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Odoo Mexican Localization Data Load to test",
    "description": "Dummy and temporal module to configure runbot "
    "with basic info - ONLY FOR TESTING",
    "version": "1",
    "depends": [
        "company_country",
        "currency_rate_live",
        # Extra modules not auto-installed of l10n_mx_*
        "l10n_mx_edi_customs",
        "l10n_mx_edi_external_trade",
        "l10n_mx_edi_landing",
        "l10n_mx_reports",
        "l10n_mx_edi_sale_coupon",
        "l10n_mx_edi_cancellation",
    ],
    "data": [
        "data/global.xml",
        "data/config.xml",
    ],
    "installable": True,
}
