
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestL10nMXAll(TransactionCase):

    def test_l10n_mx_all(self):
        """Check if all l10n_mx* modules are installed"""
        mx_modules = self.env['ir.module.module'].search([
            ('name', 'like', 'l10n_mx%'), ('state', '!=', 'installed')])
        self.assertFalse(
            mx_modules,
            "MX modules not installed: %s" % mx_modules.mapped('name'))
