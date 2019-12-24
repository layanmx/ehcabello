# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import objectify, etree
from openerp.tools.safe_eval import safe_eval
from openerp.exceptions import ValidationError
from odoo.tools import file_open

from .common import MexicoReportsTestCase


class AccountCoA(MexicoReportsTestCase):

    def setUp(self):
        super(AccountCoA, self).setUp()
        self.report_coa = self.env['l10n_mx.coa.report']
        self.tax_model = self.env['account.tax']
        self.afrl_obj = self.env['account.financial.html.report.line']
        self.tag1 = self.env.ref('l10n_mx.account_tag_101_01')

    def test_001_get_coa_xml(self):
        """Verify that XML to CoA report is generated"""
        self._prepare_accounts_coa()
        options = self.report_coa._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_coa.get_xml(options)
        self.assertTrue(data)

    def test_002_get_coa_account_deprecated(self):
        """Verify that XML to CoA report not consider deprecated accounts"""
        self._prepare_accounts_coa()
        self.account_obj.create({
            'code': '101.01.999',
            'name': 'Account Test CoA',
            'deprecated': True,
            'user_type_id': self.account_type_cash.id,
            'tag_ids': [(4, self.tag1.id)],
        })
        options = self.report_coa._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_coa.get_xml(options)
        xml = objectify.fromstring(data)
        accounts = [acc.get('NumCta') for acc in xml.Ctas]
        self.assertNotIn('101.01.999', accounts, 'Deprecated account printed.')

    def test_003_get_coa_account_unfold(self):
        """Verify that XML to CoA report print all accounts"""
        self._prepare_accounts_coa()
        self.account_obj.create({
            'code': '101.01.999',
            'name': 'Account Test CoA',
            'user_type_id': self.account_type_cash.id,
            'tag_ids': [(4, self.tag1.id)],
        })
        options = self.report_coa._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        options.update(
            {'unfolded_financial':
             self.env.ref('l10n_mx_reports.mx_afrl_101').id})
        data = self.report_coa.get_xml(options)
        xml = objectify.fromstring(data)
        accounts = [acc.get('NumCta') for acc in xml.Ctas]
        bases = self.tax_model.search([]).mapped('cash_basis_base_account_id')
        acc = self.account_obj.search([
            ('deprecated', '=', False),
            ('id', 'not in', bases.ids)])
        acc_level_two = list(set([a.code[:6] for a in acc]))
        acc_level_one = list(set([a[:3] for a in acc_level_two]))
        count_acc = len(acc_level_two) + len(acc_level_one)
        self.assertEquals(
            len(accounts), count_acc, 'Not all accounts printed.')

    def test_004_get_coa_xml_misconfigured(self):
        """Verify that XML to CoA report is not generated because of
        misconfigured accounts"""
        self.account_obj.create({
            'code': '989.09',
            'name': 'Account Test CoA',
            'user_type_id': self.account_type_cash.id,
        })
        options = self.report_coa._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        self.assertRaises(ValidationError, self.report_coa.get_xml, options)

    def test_005_expected_coa_report(self):
        """Verify expected xml"""
        self._prepare_accounts_coa()
        options = self.report_coa._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_coa.get_xml(options)
        xml = objectify.fromstring(data)
        xml_file = file_open('l10n_mx_enterprise/tests/expected_coa.xml')
        xml_expected = objectify.parse(xml_file).getroot()
        xml_expected = etree.tostring(xml_expected, pretty_print=True)
        xml_expected = objectify.fromstring(xml_expected)
        xml_expected.attrib['Sello'] = xml.attrib['Sello']
        xml_expected.attrib['Mes'] = xml.attrib['Mes']
        xml_expected.attrib['Anio'] = xml.attrib['Anio']
        xml = self.xml2dict(xml)
        xml_expected = self.xml2dict(xml_expected)
        self.maxDiff = None
        self.assertEqual(xml, xml_expected)

    def _prepare_accounts_coa(self):
        """To allow generate the CoA report, prepare all accounts to set a tag
        that to account financial report lines created."""
        afr_lines = self.afrl_obj.search(
            [('parent_id', '=', False), ('code', 'ilike', 'MX_%')])
        accounts = []
        for domain in afr_lines.mapped('children_ids').mapped('domain'):
            account_ids = self.account_obj.search(safe_eval(domain or '[]'))
            accounts.extend(account_ids.ids)
        misconfigured = self.account_obj.search([('id', 'not in', accounts)])
        misconfigured.tag_ids |= self.tag1
