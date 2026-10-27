from django import forms


class FormularioAcessivel:
    """Mixin de formulário: liga cada campo com erro à sua mensagem (aria-describedby).

    O Django já marca ``aria-invalid`` nos campos com erro; aqui apontamos para o
    ``<p id="erro-<id do campo>">`` que os templates renderizam logo abaixo do campo.
    Use antes da classe base: ``class MeuForm(FormularioAcessivel, forms.Form)``.
    """

    def full_clean(self):
        super().full_clean()
        if not self.is_bound:
            return
        for nome in self.errors:
            if nome == forms.forms.NON_FIELD_ERRORS or nome not in self.fields:
                continue
            campo = self[nome]
            ids = [f'erro-{campo.auto_id}']
            if campo.help_text:
                ids.append(f'{campo.auto_id}_helptext')
            campo.field.widget.attrs['aria-describedby'] = ' '.join(ids)
