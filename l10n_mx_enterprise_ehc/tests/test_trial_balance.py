# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import objectify, etree
from dateutil.relativedelta import relativedelta

from odoo.tools import file_open

from .common import MexicoReportsTestCase


class AccountTrialBalance(MexicoReportsTestCase):

    def setUp(self):
        super(AccountTrialBalance, self).setUp()
        self.prepare_moves()
        self.aml_obj = self.env['account.move.line']
        self.report_model = self.env['l10n_mx.trial.report']
        self.account_sec = self.env.ref('l10n_mx.1_cuenta115_01')
        self.account = self.account_obj.create({
            'name': 'Test Trial Balance',
            'code': '101.01.999',
            'user_type_id': self.account_type_cash.id,
            'tag_ids': [(4, self.env.ref('l10n_mx.account_tag_101_01').id)],
        })

    def test_001_get_trial_balance_xml(self):
        """Verify that XML to trial balance report is generated"""
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_model.get_xml(options)
        self.assertTrue(data)

    def test_002_get_movement_in_other_period(self):
        """Verify that XML to trial balance report is generated,
        but not consider movements in other period"""
        self.create_move(
            (self.date + relativedelta(months=1)).strftime('%Y-%m-%d'))
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options['filter'] = 'no_comparison'
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        options.get('date', {})['filter'] = 'custom'
        data = self.report_model.get_xml(options)
        xml = etree.fromstring(data)
        accounts = [acc.get('NumCta') for acc in xml]
        self.assertNotIn(self.account.code, accounts,
                         'Account without movements in this period.')

    def test_003_get_movement_account(self):
        """Verify that XML to trial balance report is generated
        with the correct accounts"""
        self.create_move()
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_model.get_xml(options)
        xml = etree.fromstring(data)
        account = [
            acc for acc in xml if acc.get('NumCta') == self.account.code[:6]]
        self.assertTrue(account, 'Account with movements is not printed.')
        self.assertEquals(['100.00', '101.01', '0.00', '100.00', '0.00'],
                          [account[0].get(key) for key in account[0].keys()],
                          'Different values in XML')

    def test_004_get_trial_balance_unfold(self):
        """Verify that XML to Trial Balance report print all accounts"""
        self.create_move()
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        options['unfolded_lines'] = self.env.ref(
            'l10n_mx_reports.mx_afrl_101').ids
        data = self.report_model.get_xml(options)
        xml = etree.fromstring(data)
        accounts = [acc.get('NumCta') for acc in xml]
        # get accounts to compare with odoo report
        odoo_report = self.env['account.coa.report']
        ctx = {'company_ids': self.env.user.company_id.ids,
               'state': 'posted', }
        acc = odoo_report.with_context(ctx)._get_lines(options)
        acc_level_two = list(set([a.get('name')[:6] for a in acc if a.get(
            'caret_options', False)]))
        acc_level_one = list(set([a[:3] for a in acc_level_two]))
        count_acc = len(acc_level_one) + len(acc_level_two)
        self.assertEquals(
            len(accounts), count_acc, 'Not all accounts printed.')

    def test_005_check_amounts(self):
        self.create_move(
            (self.date + relativedelta(months=-1)).strftime('%Y-%m-%d'))
        self.create_move(amounts=(1700.0, 800.0))
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options['filter'] = 'no_comparison'
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        options.get('date', {})['filter'] = 'custom'
        data = self.report_model.get_xml(options)
        xml = etree.fromstring(data)
        for acc in xml:
            if acc.get('NumCta') == '101.01':
                amounts = [acc.get('Debe'), acc.get('Haber'),
                           acc.get('SaldoIni'), acc.get('SaldoFin')]
                break
        self.assertEquals(amounts, ['1700.00', '800.00', '100.00', '1000.00'],
                          "Amounts don't match")

    def test_006_expected_balance_xml(self):
        """Verify expected xml of trial balance"""
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        data = self.report_model.get_xml(options)
        xml = objectify.fromstring(data)
        xml_file = file_open('l10n_mx_enterprise/tests/expected_balance.xml')
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

    def test_007_print_accounts_with_moves(self):
        """Verify that accounts with moves and balance = 0 are added"""
        self.create_move(amounts=(100.0, 100.0))
        options = self.report_model._get_options()
        date = self.date.strftime('%Y-%m-%d')
        options['filter'] = 'no_comparison'
        options.get('date', {})['date_from'] = date
        options.get('date', {})['date_to'] = date
        options.get('date', {})['filter'] = 'custom'
        data = self.report_model.get_xml(options)
        xml = etree.fromstring(data)
        account = False
        for acc in xml:
            if acc.get('NumCta') == '101.01':
                account = [acc.get('Debe'), acc.get('Haber'),
                           acc.get('SaldoIni'), acc.get('SaldoFin')]
                break
        self.assertTrue(account, "Account is not in the XML")
        self.assertEquals(account, ['100.00', '100.00', '0.00', '0.00'],
                          "Account must have amounts only in debit and credit")

    def create_move(self, date=False, amounts=(100,)):
        aml_values = []
        form = ('debit', 'credit')
        index = 0
        for amount in amounts:
            aml_values.append({'name': 'Move %s' % (index*2),
                               'journal_id': self.journal.id,
                               'account_id': self.account.id,
                               form[index]: amount,
                               })
            index = 0 if index else 1
            aml_values.append({'name': 'Move %s' % (index*2+1),
                               'journal_id': self.journal.id,
                               'account_id': self.account_sec.id,
                               form[index]: amount,
                               })
        self.move_obj.create({
            'name': 'Manually Trial Balance',
            'journal_id': self.journal.id,
            'date': date or self.date.strftime('%Y-%m-%d'),
            'line_ids': [(0, 0, value) for value in aml_values]}).post()
