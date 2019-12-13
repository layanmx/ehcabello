import csv
import base64


from odoo import _, api, fields, models
from odoo.exceptions import UserError

CRON_XML_IDS = {
    'out': 'l10n_mx_edi_import_bills_csv.ir_cron_import_customer_invoices',
    'in': 'l10n_mx_edi_import_bills_csv.ir_cron_import_vendor_bills',
    'pay': 'l10n_mx_edi_import_bills_csv.ir_cron_import_payments',
}

FOLDER_XML_IDS = {
    'out': 'l10n_mx_edi_import_bills_csv.'
           'documents_import_customer_invoices_cfdis_folder',
    'in': 'l10n_mx_edi_import_bills_csv.'
          'documents_import_vendor_bills_cfdis_folder',
    'pay': 'l10n_mx_edi_import_bills_csv.'
           'documents_import_payments_cfdis_folder',
}

FILE_NAME = {
    'out': 'customer_invoices.csv',
    'in': 'vendor_bills.csv',
    'pay': 'complement_payments.csv',
}


class ImportCsvInvoiceWizard(models.TransientModel):
    _name = 'import.csv.invoice.wizard'
    _description = 'Import Csv Invoices'

    file = fields.Binary(string='File Content', required=True)
    type = fields.Selection(
        [('out', 'Customer Invoices'),
         ('in', 'Vendor Bills'),
         ('pay', 'Complement Payments')],
        required=True,
        default='out',
        help="You can either import customer invoices or vendor bills.")

    # pylint: disable=W0106
    def import_invoices_from_csv(self, invoice_type='out', lines=100,
                                 create_partner=False, skip_wrong=True):
        if invoice_type not in ['in', 'out']:
            raise UserError(_('Invoice type not recognized'))
        if lines < 1:
            raise UserError(_('Imported lines cannot be lower than 1'))
        lines += 1
        inv_obj = self.env['account.invoice']
        folder_id = self.env.ref(FOLDER_XML_IDS[invoice_type]).id
        attach = self.env['ir.attachment'].search([
            ('name', '=', FILE_NAME[invoice_type]),
            ('folder_id', '=', folder_id)], limit=1)
        if not attach:
            return {}
        file_path = attach._full_path(attach.store_fname)
        line_count = 0
        xml_files = {}

        # Skip already existing CFDIs
        existing_cfdis = inv_obj.search([
            ('l10n_mx_edi_cfdi_name', '!=', False)]).mapped(
                'l10n_mx_edi_cfdi_uuid')

        # Skip CFDIs that had error while importing
        if skip_wrong:
            cron = self.env.ref(CRON_XML_IDS[invoice_type])
            logs = self.env['ir.logging'].search([
                ('func', '=', cron.name),
                ('level', '=', 'wrong_cfdi')])
            wrong_cfdis = []
            for rec in logs:
                wrong_cfdis.extend(rec.message.split('{')[1][:-1].split(','))
            wrong_cfdis = [dat for dat in wrong_cfdis if dat]
            existing_cfdis += wrong_cfdis

        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                    continue
                if not row[0]:
                    continue
                try:
                    uuid = row[0].split('tfd:TimbreFiscalDigital')[1].split(
                        'UUID="')[1].split('"')[0]
                except BaseException as exce:
                    continue
                if uuid and uuid not in existing_cfdis:
                    xml = base64.b64encode(row[0].encode()).decode('UTF-8')
                    xml_files[uuid] = xml
                    line_count += 1
                    if line_count == lines:
                        break
        wiz = self.env['attach.xmls.wizard']
        res = wiz.with_context(
            l10n_mx_edi_invoice_type=invoice_type).check_xml(xml_files)

        wrongfiles = res.get('wrongfiles', {})
        if wrongfiles and create_partner:
            uuids = list(wrongfiles.keys())
            xml_files = {}
            for uuid in uuids:
                if wrongfiles[uuid].get('supplier', {}):
                    xml64 = wrongfiles[uuid].get('xml64')
                    xml_files[uuid] = xml64
                    wiz.with_context(l10n_mx_edi_invoice_type=invoice_type).\
                        create_partner(xml64, uuid)
            res_2 = wiz.with_context(
                l10n_mx_edi_invoice_type=invoice_type).check_xml(xml_files)
            invoices = res_2.get('invoices', {})
            new_uuids = list(invoices.keys())
            for key in new_uuids:
                res['invoices'][key] = res['wrongfiles'].pop(key)
        invoices = res.get('invoices', {})
        if invoices and invoice_type == 'in':
            uuids = list(invoices.keys())
            for uuid in uuids:
                inv_id = invoices[uuid].get('invoice_id', False)
                inv_obj.browse(inv_id).action_invoice_open()
        if not res.get('wrongfiles', {}) and not res.get('invoices', {}):
            attach.unlink()
        return res

    @api.multi
    def import_csv(self):
        self.ensure_one()
        cron = self.env.ref(CRON_XML_IDS[self.type])
        # if cron and cron.active:
        #     raise UserError(_('The cron %s is still running, please wait '
        #                       'until its done executing') % cron.name)
        file_name = FILE_NAME[self.type]
        folder_id = self.env.ref(FOLDER_XML_IDS[self.type]).id
        attch_obj = self.env['ir.attachment']
        attachment = attch_obj.search([
            ('name', '=', file_name),
            ('folder_id', '=', folder_id)], limit=1)
        if attachment:
            raise UserError(_(
                'The file is still being imported, please wait longer'))
        attch_obj.create({
            'datas': self.file,
            'name': file_name,
            'datas_fname': file_name,
            'folder_id': folder_id,
        })
        if self.type == 'pay':
            self.import_csv_payments()
        cron.write({'active': True, 'nextcall': fields.datetime.now()})

    @api.multi
    def cancel_old_import(self):
        self.ensure_one()
        cron = self.env.ref(CRON_XML_IDS[self.type])
        cron.write({'active': False})

        file_name = FILE_NAME[self.type]
        folder_id = self.env.ref(FOLDER_XML_IDS[self.type]).id
        attch_obj = self.env['ir.attachment']
        attachment = attch_obj.search([
            ('name', '=', file_name),
            ('folder_id', '=', folder_id)], limit=1)
        if attachment:
            attachment.unlink()

    @api.multi
    def import_csv_payments(self):
        self.ensure_one()
        attch_obj = self.env['ir.attachment']
        attach = self.env['ir.attachment'].search(
            [('name', '=', FILE_NAME['pay'])], limit=1)
        folder_id = self.env.ref(FOLDER_XML_IDS[self.type]).id
        file_path = attach._full_path(attach.store_fname)
        line_count = 0
        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                    continue
                if row[0] and row[1]:
                    file_name = '%s.xml' % row[1]
                    att = attch_obj.search([('name', '=', file_name)])
                    if att:
                        continue
                    attch_obj.create({
                        'datas': base64.b64encode(row[0].encode('UTF-8')),
                        'name': file_name,
                        'datas_fname': file_name,
                        'folder_id': folder_id,
                    })
        attach.unlink()
