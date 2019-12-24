# coding: utf-8

from odoo import api, registry
from odoo.addons.l10n_mx_edi.tests.common import InvoiceTransactionCase


class TestL10nMxEdiInvoiceDecimals(InvoiceTransactionCase):

    def setUp(self):
        super(TestL10nMxEdiInvoiceDecimals, self).setUp()
        with registry().cursor() as cr:
            env = api.Environment(cr, 1, {})
            dp = env.ref('product.decimal_price')
            dp.digits = 3

    def test_l10n_mx_edi_invoice_basic_3_dec(self):
        self.company.partner_id.write({
            'property_account_position_id': self.fiscal_position.id,
        })
        # -----------------------
        # Testing invoice with 3 decimals price unit
        # -----------------------
        self.product = self.env.ref("product.product_product_2")
        self.product.sudo().write({
            'default_code': 'PR01',
            'l10n_mx_edi_code_sat_id': self.ref(
                'l10n_mx_edi.prod_code_sat_01010101'),
            'taxes_id': [(6, None, [self.tax_positive.id])],
        })
        invoice = self.create_invoice()
        self.create_invoice_line(invoice.id)
        invoice.refresh()
        invoice.invoice_line_ids[0].quantity = 15
        invoice.invoice_line_ids[0].price_unit = 103.6510
        invoice.invoice_line_ids[1].quantity = 10
        invoice.invoice_line_ids[1].price_unit = 212.5210
        invoice.compute_taxes()
        invoice.move_name = 'INV/2017/9999'
        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))
        xml = invoice.l10n_mx_edi_get_xml_etree()
        self.assertEqual(invoice.amount_total, float(xml.get('Total')),
                         "Total amount is not right")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))

        # ----------------------
        # Testing invoice with 3 decimals price unit and discount
        # ----------------------
        invoice = self.create_invoice()
        self.create_invoice_line(invoice.id)
        invoice.refresh()
        invoice.invoice_line_ids[0].quantity = 15
        invoice.invoice_line_ids[0].price_unit = 103.6510
        invoice.invoice_line_ids[0].discount = 10
        invoice.invoice_line_ids[1].quantity = 10
        invoice.invoice_line_ids[1].price_unit = 212.5210
        invoice.compute_taxes()
        invoice.move_name = 'INV/2017/10000'
        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        xml = invoice.l10n_mx_edi_get_xml_etree()
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))
