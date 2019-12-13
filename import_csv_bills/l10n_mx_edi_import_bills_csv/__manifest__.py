{
    'name': 'Import Customer Invoices from XMLs on CSV',
    'summary': 'Auto create multiple Invoices from XML in other systems',
    'version': '12.0.0.0.0',
    'category': 'Localization/Mexico',
    'author': 'Vauxoo',
    'website': 'https://www.vauxoo.com',
    'depends': [
        'l10n_mx_edi_vendor_bills',
        'l10n_mx_edi_customer_bills',
        'l10n_mx_edi_document',
    ],
    'license': 'LGPL-3',
    'data': [
        'data/ir_cron.xml',
        'wizards/import_csv_invoice_wizard_view.xml',
    ],
    'installable': True,
}
