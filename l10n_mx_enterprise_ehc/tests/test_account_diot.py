# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from .common import MexicoReportsTestCase


class AccountDiot(MexicoReportsTestCase):

    def setUp(self):
        super(AccountDiot, self).setUp()
        self.diot_report = self.env['l10n_mx.account.diot']
        self.invoice_refund_obj = self.env['account.invoice.refund']

        self.tax16 = self.env.ref('l10n_mx.1_tax14')
        self.tax16_sale = self.env.ref('l10n_mx.1_tax12')
        self.tax0 = self.env.ref('l10n_mx.1_tax13')
        self.tag8 = self.env.ref(
            'l10n_mx.tag_diot_8', raise_if_not_found=False) or self.env[
                'account.account.tag']
        self.account_type = self.env.ref(
            'account.data_account_type_current_assets')
        self.account = self.account_obj.create({
            'name': 'TAX TEST',
            'code': '1151003016',
            'user_type_id': self.account_type.id,
        })

        self.report_model = 'l10n_mx.account.diot'
        self.vat = 'XXX010101XX1'
        self.partner.write({'vat': self.vat})
        self.set_tax_config(self.tax16)
        self.set_tax_config(self.tax_ret)
        self.set_tax_config(self.tax0)
        self.date = self.date.date()

    def test_001_generate_diot_16(self):
        """Generated a move with tax 16%, is generated DIOT Report.
        This have a customer invoice paid."""
        invoice = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice)
        # Validate a client invoice is not displayed un DIOT
        invoice_out = self.generate_invoice(self.tax16_sale)
        invoice_out.update({'type': 'out_invoice'})
        invoice.company_id.country_id = False  # don't create cfdi
        self.validate_invoice(invoice_out)
        options = self.diot_report._get_options()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        self.assertEqual(
            data, '04|85|%s|||||100|||||||||||||||||\n' % (self.vat),
            "Error with mexican suppliers")

    def test_002_generate_diot_0(self):
        """Generated a move with tax 0%, is generated DIOT Report"""
        invoice = self.generate_invoice(self.tax0)
        self.validate_invoice(invoice)
        options = self.diot_report._get_options()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        pat = r'04\|85\|(.*)\|100\|(.*)'
        self.assertTrue(re.search(pat, data))

    def test_003_generate_diot_ret(self):
        """Generated a move with retention tax 10.67%, verify that is generated
        DIOT Report"""
        invoice = self.generate_invoice(self.tax_ret)
        self.validate_invoice(invoice)
        options = self.diot_report._get_options()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        pat = r'04\|85\|(.*)\|11\|(.*)'
        self.assertTrue(re.search(pat, data))

    def test_004_generate_diot_two_moves(self):
        """Generated two movements to tax 16%, and verify that amount is the
        sum of two movements"""
        invoice1 = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice1)
        invoice2 = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice2)
        options = self.diot_report._get_options()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        pat = r'04\|85\|(.*)\|200\|(.*)'
        self.assertTrue(re.search(pat, data))

    def test_005_generate_diot_foreign_supplier(self):
        """Generated two movements to tax 16%, this movement is to Foreign
        Supplier."""
        self.partner.write({
            'country_id': self.country_usa.id,
        })
        invoice1 = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice1)
        invoice2 = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice2)
        options = self.diot_report._get_options()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        self.assertEqual(
            data, '05|85||%s|%s|US|Americano|200|||||||||||||||||\n' % (
                self.vat, self.partner.name), "Error with foreign suppliers")

    def test_006_generate_diot_refund_paid(self):
        """Verify that with invoice refund is not generated DIOT report."""
        invoice = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice)
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        refund = self.invoice_refund_obj.with_context(
            active_ids=invoice.ids).create({
                'filter_refund': 'refund',
                'description': 'Refund Test',
                'date_invoice': date
            })
        result = refund.invoice_refund()
        refund_id = result.get('domain')[1][2]
        refund = self.invoice_obj.browse(refund_id)
        refund.action_invoice_open()
        refund.pay_and_reconcile(
            self.journal_payment, pay_amount=invoice.amount_total,
            date=invoice.date_invoice)
        options = self.diot_report._get_options()
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        self.assertFalse(data, "File generated to invoice refund.")

    def test_007_generate_diot_refund_not_paid(self):
        """Verify that with invoice refund not paid, is not generated DIOT
        report."""
        invoice = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice, pay=False)
        self.invoice_refund_obj.with_context(active_ids=invoice.ids).create({
            'filter_refund': 'cancel',
            'description': 'Refund Test',
            'date_invoice': invoice.date_invoice,
        }).invoice_refund()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options = self.diot_report._get_options()
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        self.assertFalse(data, "File generated to invoice refund.")

    def test_008_generate_diot_16_last_month(self):
        """Generated a invoice to last month with tax 16%"""
        date = self.date.strftime('%Y-%m-%d')
        self.date = self.date - relativedelta(months=1)
        invoice = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice)
        options = self.diot_report._get_options()
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        self.assertFalse(data)
        last_month_day = monthrange(self.date.year, self.date.month)[1]
        options.get('date', {})['date_from'] = self.date.replace(
            day=1).strftime('%Y-%m-%d')
        options.get('date', {})['date_to'] = self.date.replace(
            day=last_month_day).strftime('%Y-%m-%d')
        data = self.diot_report.get_txt(options)
        pat = r'04\|85\|(.*)\|100\|(.*)'
        self.assertTrue(re.search(pat, data))

    def test_009_check_diot_when_previous_months_have_moves(self):
        """Check the diot when the last month has moves and
        current month has a refund"""
        # Create a invoice and its refund in this month
        invoice = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice)
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        refund = self.invoice_refund_obj.with_context(
            active_ids=invoice.ids).create({
                'filter_refund': 'refund',
                'description': 'Refund Test',
                'date_invoice': date
            })
        result = refund.invoice_refund()
        refund_id = result.get('domain')[1][2]
        refund = self.invoice_obj.browse(refund_id)
        refund.action_invoice_open()
        refund.pay_and_reconcile(
            self.journal_payment, pay_amount=invoice.amount_total,
            date=invoice.date_invoice)
        # check diot in false
        options = self.diot_report._get_options()
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        self.assertFalse(data, "File generated to invoice refund.")
        # create a invoice in the last month with tax 16%
        self.date = self.date - relativedelta(months=1)
        invoice = self.generate_invoice(self.tax16)
        self.validate_invoice(invoice)
        # create diot for this month
        options = self.diot_report._get_options()
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        this_month_data = self.diot_report.get_txt(options)
        # create diot for last month
        last_month_day = monthrange(self.date.year, self.date.month)[1]
        options.get('date', {})['date_from'] = self.date.replace(
            day=1).strftime('%Y-%m-%d')
        options.get('date', {})['date_to'] = self.date.replace(
            day=last_month_day).strftime('%Y-%m-%d')
        last_month_data = self.diot_report.get_txt(options)
        # check that this_month is still false and last month is true
        self.assertFalse(this_month_data, "File generated for refund invoice.")
        self.assertTrue(last_month_data, "File no generated.")

    def test_010_generate_diot_8(self):
        """Generated a move with tax 8%, is generated DIOT Report"""
        tax_8 = self.tax0.copy()
        tax_8.write({
            'name': 'Iva(8%) Compras',
            'amount': 8.0000,
            'description': 'IVA(8%)',
        })
        tax_8.tag_ids = self.tag8
        invoice = self.generate_invoice(tax_8)
        self.validate_invoice(invoice)
        options = self.diot_report._get_options()
        date = self.date.replace(day=15).strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.diot_report.get_txt(options)
        pat = r'04\|85\|(.*)\|100\|(.*)'
        self.assertTrue(re.search(pat, data))

    def generate_invoice(self, tax):
        """Create the invoice needed to generate a journal entry with the
        information to generate DIOT report
        """
        invoice = self.invoice_obj.create({
            'partner_id': self.partner.id,
            'type': 'in_invoice',
            'date_invoice': self.date.replace(day=15),
            'account_id': self.partner.property_account_payable_id.id,
            'journal_id': self.invoice_journal.id,
        })
        self.env['account.invoice.line'].create({
            'product_id': self.prod.id,
            'account_id': (self.prod.product_tmpl_id.
                           get_product_accounts().get('income').id),
            'quantity': 1,
            'price_unit': 100,
            'name': 'Product Test',
            'invoice_id': invoice.id,
            'invoice_line_tax_ids': [(4, tax.id)]
        })
        invoice.compute_taxes()
        return invoice

    def validate_invoice(self, invoice, pay=True):
        invoice.action_invoice_open()
        if pay:
            invoice.pay_and_reconcile(
                self.journal_payment, pay_amount=invoice.amount_total,
                date=self.date.replace(day=15))
        return invoice

    def set_tax_config(self, tax):
        """Configure the tax to be used in DIOT report
        :param tax: Tax record to be updated
        :type tax: account.tax()
        :return: The boolean returned by write method
        :rtype: bool
        """
        return tax.write({
            'cash_basis_account_id': self.account.id})
