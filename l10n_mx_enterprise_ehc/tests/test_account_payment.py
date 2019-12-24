import os
import datetime

from lxml import etree, objectify

from odoo.tools import misc

from odoo.addons.l10n_mx_edi.tests.common import InvoiceTransactionCase


class TestAccountPayment(InvoiceTransactionCase):
    def setUp(self):
        super(TestAccountPayment, self).setUp()

        self.journal = self.env['account.journal']
        self.register_payments_model = self.env['account.register.payments']
        self.payment_model = self.env['account.payment']
        self.payment_method_manual_out = self.env.ref(
            "account.account_payment_method_manual_out")
        isr_tag = self.env['account.account.tag'].search(
            [('name', '=', 'ISR')])
        self.tax_negative.tag_ids |= isr_tag
        self.company.partner_id.write({
            'property_account_position_id': self.fiscal_position.id,
        })

    def test_l10n_mx_edi_account_payment(self):
        """Generated two payments to an invoice, to test
        the payment complement.
        """

        self.xml_expected_str = misc.file_open(os.path.join(
            'l10n_mx_enterprise', 'tests',
            'expected_payment.xml')).read().encode('UTF-8')
        self.xml_expected = objectify.fromstring(self.xml_expected_str)
        journal = self.journal.search([('type', '=', 'bank')], limit=1)
        invoice = self.create_invoice()
        today = self.env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime()
        self.rate_model.create({
            'rate': 21, 'name': today, 'currency_id': self.mxn.id})
        self.rate_model.create({
            'rate': 1, 'name': today, 'currency_id': self.usd.id})
        invoice.date_invoice = (today - datetime.timedelta(days=1)).date()
        invoice.move_name = 'INV/2017/999'

        invoice.action_invoice_open()
        self.assertEqual(invoice.state, "open")
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))

        ctx = {'active_model': 'account.invoice', 'active_ids': [invoice.id]}
        register_payments = self.register_payments_model.with_context(ctx).create({
            'payment_date': today,
            'l10n_mx_edi_payment_method_id': self.payment_method_cash.id,
            'payment_method_id': self.payment_method_manual_out.id,
            'journal_id': journal.id,
            'communication': invoice.number,
            'amount': 238.5,
        })

        # First payment
        payment = register_payments.create_payments()
        payment = self.payment_model.search(payment.get('domain', []))
        self.assertEqual(
            payment.l10n_mx_edi_pac_status, 'signed', payment.message_ids.mapped('body'))

        # Last payment
        payment = register_payments.create_payments()
        payment = self.payment_model.search(payment.get('domain', []))
        self.assertEqual(
            payment.l10n_mx_edi_pac_status, 'signed', payment.message_ids.mapped('body'))
        self.assertEqual(invoice.state, 'paid')

        xml = payment.l10n_mx_edi_get_xml_etree()
        self.xml_merge_dynamic_items(xml, self.xml_expected)
        self.assertEqualXML(xml, self.xml_expected)

    def xml_merge_dynamic_items(self, xml, xml_expected):
        """Overwrite the method to not replace all the complement node if not
        replace the node TimbreFiscalDigital and some attributes of the payment
        complement"""
        xml_expected.attrib['Fecha'] = xml.attrib['Fecha']
        xml_expected.attrib['Sello'] = xml.attrib['Sello']
        xml_expected.attrib['Serie'] = xml.attrib['Serie']

        # Set elements dynamic of Pagos node
        payment = self.payment_model.l10n_mx_edi_get_payment_etree(xml)
        # Use 'len(elem)' when elem is a lxml.etree._Element to avoid FutureWarning
        if len(payment):
            payment_expected = self.payment_model.l10n_mx_edi_get_payment_etree(
                xml_expected)
            payment_expected[0].getparent().set(
                'FechaPago', payment[0].getparent().get('FechaPago', ''))
            payment_expected[0].set(
                'IdDocumento', payment[0].get('IdDocumento'))

        # Replace node TimbreFiscalDigital
        tfd_expected = self.invoice_model.l10n_mx_edi_get_tfd_etree(
            xml_expected)
        tfd_xml = objectify.fromstring(etree.tostring(
            self.invoice_model.l10n_mx_edi_get_tfd_etree(xml)))
        xml_expected.Complemento.replace(tfd_expected, tfd_xml)
