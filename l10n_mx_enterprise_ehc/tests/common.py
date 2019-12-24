# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields
from openerp.tests.common import TransactionCase


class MexicoReportsTestCase(TransactionCase):

    def setUp(self):
        super(MexicoReportsTestCase, self).setUp()
        self.move_obj = self.env['account.move']
        self.journal_obj = self.env['account.journal']
        self.account_obj = self.env['account.account']
        self.tax_obj = self.env['account.tax']
        self.partner = self.env.ref('base.res_partner_12')
        self.country_mx = self.env.ref('base.mx')
        self.country_usa = self.env.ref('base.us')
        self.company = self.env.ref('base.main_company')
        self.company.write({'country_id': self.country_mx.id})
        self.invoice_obj = self.env['account.invoice']
        self.account_type_cash = self.env.ref(
            'account.data_account_type_liquidity')
        self.prod = self.env.ref('product.product_product_8')
        self.tax_ret = self.tax_obj.search([
            ('name', '=', 'RETENCION IVA ARRENDAMIENTO 10.67%')])
        self.journal = self.journal_obj.search(
            [('code', '=', 'CBMX'),
             ('type', '=', 'general'),
             ('company_id', '=', self.company.id)],
            limit=1)
        self.date = fields.Datetime.context_timestamp(
            self.journal, fields.Datetime.from_string(
                fields.Datetime.now()))
        self.journal_payment = self.journal_obj.search(
            [('code', '=', 'CSH1'),
             ('type', '=', 'cash'),
             ('company_id', '=', self.company.id)],
            limit=1)
        self.invoice_journal = self.journal_obj.search(
            ['|', '&',
             ('code', '=', 'BILL'),
             ('type', '=', 'purchase'),
             ('company_id', '=', self.company.id)],
            limit=1)
        self.invoice_journal = self.journal_obj.create({
            'name': 'Supplier Invoice J',
            'type': 'purchase',
            'code': 'SUP',
        })

    def prepare_moves(self):
        account_id = self.account_obj.search(
            [('code', '=', '201.01.01')], limit=1)
        line_account_id = self.account_obj.search(
            [('code', '=', '501.01.01')], limit=1)
        tax_line_0 = self.tax_obj.search(
            [('name', '=', 'IVA(16%) COMPRAS')], limit=1)
        tax_line_1 = self.tax_obj.search(
            [('name', '=', 'IVA(0%) COMPRAS')], limit=1)

        invoice_lines = [(0, 0, {
            'product_id': self.env.ref('product.product_product_3').id,
            'price_unit': 100.0,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'quantity': 1,
            'name': 'PC Assemble SC234',
            'sequence': 15,
            'invoice_line_tax_ids': [(6, 0, [tax_line_0.id])],
            'account_id': line_account_id.id,
        }), (0, 0, {
            'product_id': self.env.ref('product.product_product_5').id,
            'price_unit': 100.0,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'quantity': 1,
            'name': 'PC Assemble + Custom (PC on Demand)',
            'sequence': 20,
            'invoice_line_tax_ids': [(6, 0, [tax_line_1.id])],
            'account_id': line_account_id.id,
        })]
        invoice = self.invoice_obj.create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'invoice_line_ids': invoice_lines,
            'type': 'in_invoice',
            'account_id': account_id.id,
        })
        invoice.compute_taxes()
        invoice.action_invoice_open()

    @staticmethod
    def xml2dict(xml):
        """Receive 1 lxml etree object and return a dict string.
        This method allow us have a precise diff output"""
        def recursive_dict(element):
            return (element.tag,
                    dict((recursive_dict(e) for e in element.getchildren()),
                         ____text=element.text, **element.attrib))
        return dict([recursive_dict(xml)])
