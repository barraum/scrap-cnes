import io
import os
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict, Any, Union, Optional

class CNESExporter:
    """
    Exportador profissional de dados do CNES para planilhas Excel (.xlsx) com abas limpas e estilizadas.
    """
    
    HEADER_FILL = PatternFill(start_color="0F4C81", end_color="0F4C81", fill_type="solid") # Dark Teal
    HEADER_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Segoe UI", size=14, bold=True, color="0F4C81")
    SUBTITLE_FONT = Font(name="Segoe UI", size=10, italic=True, color="555555")
    CELL_FONT = Font(name="Segoe UI", size=10)
    BORDER_THIN = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    )

    @classmethod
    def export_to_excel(cls, data: Dict[str, Any], output_path_or_buf: Optional[Union[str, io.BytesIO]] = None) -> Union[str, bytes]:
        """
        Gera uma pasta de trabalho Excel com múltiplas abas estilizadas a partir do snapshot CNES.
        """
        meta = data.get('metadata', {})
        cnes = meta.get('cnes', 'CNES')
        comp = meta.get('competencia', 'Atual')
        
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # 1. Resumo Cadastral
            resumo_rows = [
                ("CNES", meta.get('cnes')),
                ("Código Unidade (coUnidade)", meta.get('coUnidade')),
                ("Nome Fantasia", meta.get('nomeFantasia')),
                ("Razão Social", meta.get('razaoSocial')),
                ("Município / UF", f"{meta.get('municipio')} / {meta.get('uf')}"),
                ("Competência", comp),
                ("Total Profissionais", len(data.get('profissionais', []))),
                ("Total Leitos Existentes", sum(int(l.get('qtExistente', 0)) for l in data.get('leitos', []))),
                ("Total Leitos SUS", sum(int(l.get('qtSus', 0)) for l in data.get('leitos', []))),
                ("Total Equipamentos", len(data.get('equipamentos', []))),
                ("Total Serviços Especializados", len(data.get('servicos_classificacao', []))),
                ("Total Habilitações", len(data.get('habilitacoes', []))),
            ]
            df_resumo = pd.DataFrame(resumo_rows, columns=["Campo", "Valor"])
            df_resumo.to_excel(writer, sheet_name="Resumo", index=False)

            # 2. Profissionais
            profs = data.get('profissionais', [])
            if profs:
                df_profs = pd.DataFrame(profs)
                cols_map = {
                    'nome': 'Nome do Profissional',
                    'cns': 'CNS/CPF',
                    'dsCbo': 'Descrição CBO / Especialidade',
                    'cbo': 'Código CBO',
                    'chAmb': 'Carga Horária Ambulatorial',
                    'chHosp': 'Carga Horária Hospitalar',
                    'chOutros': 'Carga Horária Outros',
                    'vinculo': 'Tipo de Vínculo',
                    'vinculacao': 'Descrição Vínculo',
                    'tpSusNaoSus': 'Atende SUS'
                }
                present_cols = [c for c in cols_map.keys() if c in df_profs.columns]
                if present_cols:
                    df_profs = df_profs[present_cols].rename(columns=cols_map)
                df_profs.to_excel(writer, sheet_name="Profissionais", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum profissional registrado."]}).to_excel(writer, sheet_name="Profissionais", index=False)

            # 3. Leitos
            leitos = data.get('leitos', [])
            if leitos:
                df_leitos = pd.DataFrame(leitos)
                cols_map = {
                    'dsLeito': 'Tipo de Leito',
                    'dsAtributo': 'Especialidade / Categoria',
                    'qtExistente': 'Quantidade Existente',
                    'qtSus': 'Quantidade SUS',
                    'qtNaoSus': 'Quantidade Não SUS',
                    'coLeito': 'Código do Tipo (ID DATASUS)'
                }
                present_cols = [c for c in cols_map.keys() if c in df_leitos.columns]
                if present_cols:
                    df_leitos = df_leitos[present_cols].rename(columns=cols_map)
                if 'Código do Tipo (ID DATASUS)' in df_leitos.columns:
                    df_leitos['Código do Tipo (ID DATASUS)'] = df_leitos['Código do Tipo (ID DATASUS)'].astype(str).apply(lambda x: f"Código {x}")
                df_leitos.to_excel(writer, sheet_name="Leitos Hospitalares", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum leito hospitalar registrado."]}).to_excel(writer, sheet_name="Leitos Hospitalares", index=False)

            # 4. Equipamentos
            equip = data.get('equipamentos', [])
            if equip:
                df_equip = pd.DataFrame(equip)
                cols_map = {
                    'dsEquipamento': 'Descrição Equipamento',
                    'dsTipoEquipamento': 'Tipo / Categoria',
                    'qtExistente': 'Quantidade Existente',
                    'qtEmUso': 'Quantidade em Uso',
                    'tpSus': 'Indicação SUS',
                    'coEquipamento': 'Código Equipamento (ID DATASUS)'
                }
                present_cols = [c for c in cols_map.keys() if c in df_equip.columns]
                if present_cols:
                    df_equip = df_equip[present_cols].rename(columns=cols_map)
                if 'Código Equipamento (ID DATASUS)' in df_equip.columns:
                    df_equip['Código Equipamento (ID DATASUS)'] = df_equip['Código Equipamento (ID DATASUS)'].astype(str).apply(lambda x: f"Código {x}")
                df_equip.to_excel(writer, sheet_name="Equipamentos", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum equipamento registrado."]}).to_excel(writer, sheet_name="Equipamentos", index=False)

            # 5. Serviços & Classificações
            servs = data.get('servicos_classificacao', [])
            if servs:
                df_servs = pd.DataFrame(servs)
                cols_map = {
                    'dsServico': 'Descrição Serviço',
                    'dsServicoEspecializado': 'Classificação Especializada',
                    'tpCaracteristica': 'Característica da Instalação',
                    'cnpj': 'CNPJ Prestador',
                    'coServico': 'Código Serviço (ID)',
                    'coClassificacao': 'Código Classificação (ID)'
                }
                present_cols = [c for c in cols_map.keys() if c in df_servs.columns]
                if present_cols:
                    df_servs = df_servs[present_cols].rename(columns=cols_map)
                df_servs.to_excel(writer, sheet_name="Serviços & Classificações", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum serviço registrado."]}).to_excel(writer, sheet_name="Serviços & Classificações", index=False)

            # 6. Instalações Físicas & Comissões
            inst = data.get('instalacoes', [])
            if inst:
                df_inst = pd.DataFrame(inst)
                df_inst.to_excel(writer, sheet_name="Instalações Físicas", index=False)

            comiss = data.get('comissoes', [])
            if comiss:
                df_comiss = pd.DataFrame(comiss)
                df_comiss.to_excel(writer, sheet_name="Comissões Médicas", index=False)

            # 7. Habilitações & Incentivos
            hab = data.get('habilitacoes', [])
            if hab:
                df_hab = pd.DataFrame(hab)
                df_hab.to_excel(writer, sheet_name="Habilitações", index=False)

            inc = data.get('incentivos', [])
            if inc:
                df_inc = pd.DataFrame(inc)
                df_inc.to_excel(writer, sheet_name="Incentivos Financeiros", index=False)

        # Aplicar estilização visual com openpyxl
        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)
        
        for ws in wb.worksheets:
            # Estilizar cabeçalho (linha 1)
            for cell in ws[1]:
                cell.fill = cls.HEADER_FILL
                cell.font = cls.HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Estilizar células e largura das colunas
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = cls.CELL_FONT
                    cell.border = cls.BORDER_THIN

            # Ajuste dinâmico de largura
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

        output_buf = io.BytesIO()
        wb.save(output_buf)
        excel_bytes = output_buf.getvalue()

        if isinstance(output_path_or_buf, str):
            os.makedirs(os.path.dirname(output_path_or_buf) or ".", exist_ok=True)
            with open(output_path_or_buf, "wb") as f:
                f.write(excel_bytes)
            return output_path_or_buf
            
        return excel_bytes

    @classmethod
    def export_municipality_report(cls, establishments: list, municipio_nome: str = "", uf: str = "") -> bytes:
        """
        Gera relatório Excel completo de um município com múltiplas abas:
        - Resumo por Classificação de Estabelecimento
        - Listagem completa de todos os estabelecimentos
        """
        buffer = io.BytesIO()
        df = pd.DataFrame(establishments)

        # Mapeamento de colunas para nomes amigáveis
        cols_display = {
            'cnes': 'CNES',
            'noFantasia': 'Nome Fantasia',
            'noEmpresarial': 'Nome Empresarial',
            'coTipoEstabelecimento': 'Código Classificação',
            'dsTipoEstabelecimento': 'Classificação Estabelecimento',
            'dsTpUnidade': 'Tipo de Unidade',
            'tpGestao': 'Gestão',
            'gestao': 'Gestão (Listagem)',
            'natJuridica': 'Natureza Jurídica',
            'atendeSus': 'Atende SUS',
            'coEsferaAdministrativa': 'Esfera Administrativa',
            'noLogradouro': 'Logradouro',
            'nuEndereco': 'Número',
            'bairro': 'Bairro',
            'cep': 'CEP',
            'nuTelefone': 'Telefone',
            'noEmail': 'E-mail',
            'nuLatitude': 'Latitude',
            'nuLongitude': 'Longitude',
            'noMunicipio': 'Município',
            'uf': 'UF',
        }

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # --- Aba 1: Resumo por Classificação ---
            if 'dsTipoEstabelecimento' in df.columns:
                resumo = df.groupby('dsTipoEstabelecimento').agg(
                    Quantidade=('cnes', 'count')
                ).reset_index().rename(columns={'dsTipoEstabelecimento': 'Classificação do Estabelecimento'})
                resumo = resumo.sort_values('Quantidade', ascending=False)

                # Adicionar linha de total
                total_row = pd.DataFrame([{
                    'Classificação do Estabelecimento': 'TOTAL GERAL',
                    'Quantidade': resumo['Quantidade'].sum()
                }])
                resumo = pd.concat([resumo, total_row], ignore_index=True)
                resumo.to_excel(writer, sheet_name="Resumo por Classificação", index=False)
            else:
                pd.DataFrame({"Aviso": ["Dados de classificação não disponíveis. Execute a extração completa."]}).to_excel(
                    writer, sheet_name="Resumo por Classificação", index=False
                )

            # --- Aba 2: Resumo por Tipo de Unidade ---
            if 'dsTpUnidade' in df.columns:
                resumo_tp = df.groupby('dsTpUnidade').agg(
                    Quantidade=('cnes', 'count')
                ).reset_index().rename(columns={'dsTpUnidade': 'Tipo de Unidade'})
                resumo_tp = resumo_tp.sort_values('Quantidade', ascending=False)
                total_row_tp = pd.DataFrame([{
                    'Tipo de Unidade': 'TOTAL GERAL',
                    'Quantidade': resumo_tp['Quantidade'].sum()
                }])
                resumo_tp = pd.concat([resumo_tp, total_row_tp], ignore_index=True)
                resumo_tp.to_excel(writer, sheet_name="Resumo por Tipo Unidade", index=False)

            # --- Aba 3: Resumo por Gestão ---
            gestao_col = 'tpGestao' if 'tpGestao' in df.columns else 'gestao'
            if gestao_col in df.columns:
                gestao_map = {'M': 'Municipal', 'E': 'Estadual', 'D': 'Dupla', 'S': 'Sem Gestão'}
                df_gestao = df.copy()
                df_gestao['_gestao_label'] = df_gestao[gestao_col].map(lambda x: gestao_map.get(str(x).strip(), str(x)))
                resumo_g = df_gestao.groupby('_gestao_label').agg(
                    Quantidade=('cnes', 'count')
                ).reset_index().rename(columns={'_gestao_label': 'Tipo de Gestão'})
                resumo_g = resumo_g.sort_values('Quantidade', ascending=False)
                resumo_g.to_excel(writer, sheet_name="Resumo por Gestão", index=False)

            # --- Aba 4: Listagem Completa ---
            present_cols = [c for c in cols_display.keys() if c in df.columns]
            if present_cols:
                df_export = df[present_cols].rename(columns=cols_display)
            else:
                df_export = df

            # Tratar campo de gestão para display
            if 'Gestão' in df_export.columns:
                gestao_map = {'M': 'Municipal', 'E': 'Estadual', 'D': 'Dupla', 'S': 'Sem Gestão'}
                df_export['Gestão'] = df_export['Gestão'].map(lambda x: gestao_map.get(str(x).strip(), str(x)))

            if 'Gestão (Listagem)' in df_export.columns:
                if 'Gestão' not in df_export.columns:
                    gestao_map = {'M': 'Municipal', 'E': 'Estadual', 'D': 'Dupla', 'S': 'Sem Gestão'}
                    df_export['Gestão (Listagem)'] = df_export['Gestão (Listagem)'].map(lambda x: gestao_map.get(str(x).strip(), str(x)))
                else:
                    df_export = df_export.drop(columns=['Gestão (Listagem)'])

            if 'Atende SUS' in df_export.columns:
                df_export['Atende SUS'] = df_export['Atende SUS'].map(lambda x: 'Sim' if str(x).strip() == 'S' else ('Não' if str(x).strip() == 'N' else str(x)))

            if 'Natureza Jurídica' in df_export.columns:
                nj_map = {'1': 'Administração Pública', '2': 'Entidades Empresariais', '3': 'Entidades sem Fins Lucrativos', '4': 'Pessoas Físicas'}
                df_export['Natureza Jurídica'] = df_export['Natureza Jurídica'].map(lambda x: nj_map.get(str(x).strip(), str(x)))

            df_export.to_excel(writer, sheet_name="Listagem Completa", index=False)

        # Aplicar estilização visual
        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)

        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.fill = cls.HEADER_FILL
                cell.font = cls.HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = cls.CELL_FONT
                    cell.border = cls.BORDER_THIN

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

        output_buf = io.BytesIO()
        wb.save(output_buf)
        return output_buf.getvalue()

    @classmethod
    def export_leitos_evolution_report(cls, records: list, cnes_code: str = "", nome_fantasia: str = "") -> bytes:
        """
        Gera relatório Excel detalhado da evolução histórica de leitos.
        Com abas de Matriz por Competência e Dados Detalhados.
        """
        buffer = io.BytesIO()
        df = pd.DataFrame(records)

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            if not df.empty:
                # 1. Matriz Resumo de Leitos SUS por Competência
                piv_sus = df.pivot_table(
                    index=['dsAtributo', 'dsLeito'],
                    columns='competencia',
                    values='qtSus',
                    aggfunc='sum',
                    fill_value=0
                ).reset_index()
                piv_sus.to_excel(writer, sheet_name="Evolução Leitos SUS", index=False)

                # 2. Matriz Resumo de Leitos Totais por Competência
                piv_tot = df.pivot_table(
                    index=['dsAtributo', 'dsLeito'],
                    columns='competencia',
                    values='qtExistente',
                    aggfunc='sum',
                    fill_value=0
                ).reset_index()
                piv_tot.to_excel(writer, sheet_name="Evolução Leitos Totais", index=False)

                # 3. Dados Detalhados
                cols_map = {
                    'competencia': 'Competência',
                    'dsAtributo': 'Grupo de Leito',
                    'dsLeito': 'Tipo de Leito',
                    'coLeito': 'Código Leito (ID)',
                    'qtSus': 'Leitos SUS',
                    'qtNaoSus': 'Leitos Não-SUS',
                    'qtExistente': 'Leitos Totais Existentes'
                }
                present_cols = [c for c in cols_map.keys() if c in df.columns]
                df_export = df[present_cols].rename(columns=cols_map)
                df_export.to_excel(writer, sheet_name="Histórico Detalhado", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum dado de leito encontrado."]}).to_excel(writer, sheet_name="Aviso", index=False)

        # Aplicar estilização visual
        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)

        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.fill = cls.HEADER_FILL
                cell.font = cls.HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = cls.CELL_FONT
                    cell.border = cls.BORDER_THIN

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

        output_buf = io.BytesIO()
        wb.save(output_buf)
        return output_buf.getvalue()

    @classmethod
    def export_municipality_professionals_report(cls, records: list, municipio_nome: str = "", uf: str = "") -> bytes:
        """
        Gera relatório Excel completo de profissionais de um município com abas estilizadas:
        - Resumo por CBO / Especialidade
        - Resumo por Tipo de Vínculo
        - Listagem Completa de Profissionais
        """
        buffer = io.BytesIO()
        df = pd.DataFrame(records)

        cols_map = {
            'nome': 'Nome do Profissional',
            'cns': 'CNS/CPF',
            'dsCbo': 'CBO / Especialidade',
            'cbo': 'Código CBO',
            'chAmb': 'CH Ambulatorial',
            'chHosp': 'CH Hospitalar',
            'chOutros': 'CH Outros',
            'vinculacao': 'Vinculação',
            'vinculo': 'Tipo Vínculo',
            'subVinculo': 'Sub-Vínculo',
            'tpSusNaoSus': 'Atende SUS',
            'cnes': 'CNES',
            'noFantasia': 'Nome Fantasia Estabelecimento',
            'noEmpresarial': 'Razão Social Estabelecimento',
            'noMunicipio': 'Município',
            'uf': 'UF'
        }

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            if not df.empty:
                # 1. Resumo por CBO / Especialidade
                if 'dsCbo' in df.columns:
                    resumo_cbo = df.groupby('dsCbo').agg(
                        Quantidade=('nome', 'count')
                    ).reset_index().rename(columns={'dsCbo': 'CBO / Especialidade Ocupacional'})
                    resumo_cbo = resumo_cbo.sort_values('Quantidade', ascending=False)
                    tot_row = pd.DataFrame([{'CBO / Especialidade Ocupacional': 'TOTAL GERAL', 'Quantidade': resumo_cbo['Quantidade'].sum()}])
                    resumo_cbo = pd.concat([resumo_cbo, tot_row], ignore_index=True)
                    resumo_cbo.to_excel(writer, sheet_name="Resumo por Especialidade", index=False)

                # 2. Resumo por Vínculo
                if 'vinculacao' in df.columns:
                    resumo_vin = df.groupby('vinculacao').agg(
                        Quantidade=('nome', 'count')
                    ).reset_index().rename(columns={'vinculacao': 'Tipo de Vinculação'})
                    resumo_vin = resumo_vin.sort_values('Quantidade', ascending=False)
                    tot_row_v = pd.DataFrame([{'Tipo de Vinculação': 'TOTAL GERAL', 'Quantidade': resumo_vin['Quantidade'].sum()}])
                    resumo_vin = pd.concat([resumo_vin, tot_row_v], ignore_index=True)
                    resumo_vin.to_excel(writer, sheet_name="Resumo por Vínculo", index=False)

                # 3. Análise de Acúmulo de Vínculos e Carga Horária
                if 'cns' in df.columns and 'nome' in df.columns:
                    df_calc = df.copy()
                    for c_ch in ['chAmb', 'chHosp', 'chOutros']:
                        if c_ch in df_calc.columns:
                            df_calc[c_ch] = pd.to_numeric(df_calc[c_ch], errors='coerce').fillna(0).astype(int)
                        else:
                            df_calc[c_ch] = 0
                    df_calc['chTotal'] = df_calc['chAmb'] + df_calc['chHosp'] + df_calc['chOutros']

                    multi_bonds = df_calc.groupby(['cns', 'nome']).agg(
                        Qtd_Vinculos=('cnes', 'count'),
                        Qtd_Estabelecimentos=('cnes', 'nunique'),
                        Soma_CH_Amb=('chAmb', 'sum'),
                        Soma_CH_Hosp=('chHosp', 'sum'),
                        Soma_CH_Total=('chTotal', 'sum'),
                        Especialidades=('dsCbo', lambda x: ", ".join(sorted(set(str(v) for v in x if v)))),
                        Locais_Atuacao=('noFantasia', lambda x: ", ".join(sorted(set(str(v) for v in x if v))))
                    ).reset_index()

                    multi_bonds_filtered = multi_bonds[multi_bonds['Qtd_Vinculos'] >= 2].sort_values('Soma_CH_Total', ascending=False)
                    if not multi_bonds_filtered.empty:
                        multi_bonds_filtered.rename(columns={
                            'cns': 'CNS/CPF',
                            'nome': 'Nome do Profissional',
                            'Qtd_Vinculos': 'Qtd Vínculos',
                            'Qtd_Estabelecimentos': 'Qtd Estabelecimentos',
                            'Soma_CH_Amb': 'Soma CH Ambulatorial',
                            'Soma_CH_Hosp': 'Soma CH Hospitalar',
                            'Soma_CH_Total': 'Soma CH Total Semanal',
                            'Especialidades': 'Especialidades Exercidas',
                            'Locais_Atuacao': 'Locais de Atuação'
                        }).to_excel(writer, sheet_name="Acúmulo de Vínculos", index=False)

                # 4. Listagem Completa
                present_cols = [c for c in cols_map.keys() if c in df.columns]
                df_export = df[present_cols].rename(columns=cols_map) if present_cols else df

                if 'Atende SUS' in df_export.columns:
                    df_export['Atende SUS'] = df_export['Atende SUS'].map(lambda x: 'Sim' if str(x).strip() == 'S' else ('Não' if str(x).strip() == 'N' else str(x)))

                df_export.to_excel(writer, sheet_name="Profissionais Consolidado", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum profissional encontrado."]}).to_excel(writer, sheet_name="Aviso", index=False)

        # Aplicar estilização visual
        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)

        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.fill = cls.HEADER_FILL
                cell.font = cls.HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = cls.CELL_FONT
                    cell.border = cls.BORDER_THIN

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

        output_buf = io.BytesIO()
        wb.save(output_buf)
        return output_buf.getvalue()

    @classmethod
    def export_municipality_teams_report(cls, records: list, municipio_nome: str = "", competencia: str = "Atual") -> bytes:
        """
        Gera relatório Excel completo de equipes de saúde de um município com abas estilizadas:
        - Resumo por Tipo de Equipe (ESF, EAP, ESB, EMULTI, etc.)
        - Equipes por Unidade Básica de Saúde
        - Listagem Completa de Equipes (com código INE e status)
        """
        buffer = io.BytesIO()
        df = pd.DataFrame(records)

        cols_map = {
            'cnes': 'CNES',
            'noFantasia': 'Estabelecimento de Saúde',
            'coEquipe': 'Código INE',
            'nomeEquipe': 'Nome da Equipe',
            'tpEquipe': 'Código Tipo',
            'dsEquipe': 'Tipo / Descrição da Equipe',
            'dsArea': 'Área de Atuação',
            'coArea': 'Código Área',
            'dtAtivacao': 'Data Ativação',
            'dtDesativacao': 'Data Desativação',
            'status': 'Status',
            'noMunicipio': 'Município',
            'uf': 'UF',
            'competencia': 'Competência'
        }

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            if not df.empty:
                # 1. Resumo por Tipo de Equipe
                if 'dsEquipe' in df.columns:
                    df['status_norm'] = df.get('status', 'Ativa')
                    resumo_tipo = df.groupby('dsEquipe').agg(
                        Ativas=('status_norm', lambda x: (x == 'Ativa').sum()),
                        Desativadas=('status_norm', lambda x: (x != 'Ativa').sum()),
                        Total=('status_norm', 'count')
                    ).reset_index().rename(columns={'dsEquipe': 'Tipo de Equipe'})
                    resumo_tipo = resumo_tipo.sort_values('Total', ascending=False)
                    
                    tot_row = pd.DataFrame([{
                        'Tipo de Equipe': 'TOTAL GERAL',
                        'Ativas': resumo_tipo['Ativas'].sum(),
                        'Desativadas': resumo_tipo['Desativadas'].sum(),
                        'Total': resumo_tipo['Total'].sum()
                    }])
                    resumo_tipo = pd.concat([resumo_tipo, tot_row], ignore_index=True)
                    resumo_tipo.to_excel(writer, sheet_name="Resumo por Tipo", index=False)

                # 2. Equipes por Unidade Básica de Saúde
                if 'noFantasia' in df.columns and 'cnes' in df.columns:
                    def count_esf(series):
                        return series.apply(lambda x: 1 if ('ESF' in str(x).upper() or str(x) == '70') else 0).sum()
                    def count_eap(series):
                        return series.apply(lambda x: 1 if ('EAP' in str(x).upper() or 'ATENCAO PRIMARIA' in str(x).upper()) and 'EMULTI' not in str(x).upper() else 0).sum()
                    def count_esb(series):
                        return series.apply(lambda x: 1 if ('ESB' in str(x).upper() or 'SAUDE BUCAL' in str(x).upper()) else 0).sum()
                    def count_emulti(series):
                        return series.apply(lambda x: 1 if ('EMULTI' in str(x).upper() or 'MULTIPROFISSIONAL' in str(x).upper()) else 0).sum()

                    por_unidade = df.groupby(['cnes', 'noFantasia']).agg(
                        Total_Equipes=('coEquipe', 'count'),
                        Qtd_ESF=('dsEquipe', count_esf),
                        Qtd_EAP=('dsEquipe', count_eap),
                        Qtd_ESB=('dsEquipe', count_esb),
                        Qtd_EMULTI=('dsEquipe', count_emulti),
                    ).reset_index()

                    por_unidade['Outras_Equipes'] = por_unidade['Total_Equipes'] - (
                        por_unidade['Qtd_ESF'] + por_unidade['Qtd_EAP'] + por_unidade['Qtd_ESB'] + por_unidade['Qtd_EMULTI']
                    )
                    por_unidade = por_unidade.sort_values('Total_Equipes', ascending=False)
                    por_unidade.rename(columns={
                        'cnes': 'CNES',
                        'noFantasia': 'Nome da Unidade de Saúde',
                        'Total_Equipes': 'Total de Equipes',
                        'Qtd_ESF': 'Qtd ESF',
                        'Qtd_EAP': 'Qtd EAP',
                        'Qtd_ESB': 'Qtd ESB',
                        'Qtd_EMULTI': 'Qtd EMULTI',
                        'Outras_Equipes': 'Outras Equipes'
                    }).to_excel(writer, sheet_name="Equipes por Unidade", index=False)

                # 3. Listagem Completa de Equipes
                present_cols = [c for c in cols_map.keys() if c in df.columns]
                df_export = df[present_cols].rename(columns=cols_map) if present_cols else df
                df_export.to_excel(writer, sheet_name="Todas as Equipes", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhuma equipe de saúde encontrada."]}).to_excel(writer, sheet_name="Aviso", index=False)

        # Aplicar estilização visual padrão
        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)

        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.fill = cls.HEADER_FILL
                cell.font = cls.HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = cls.CELL_FONT
                    cell.border = cls.BORDER_THIN

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 60)

        output_buf = io.BytesIO()
        wb.save(output_buf)
        return output_buf.getvalue()

    @classmethod
    def export_regional_coverage_report(cls, panorama: list, competencia: str = "Atual") -> bytes:
        """
        Gera relatório Excel executivo de cruzamento entre População IBGE e Equipes de Saúde (SUS/PNAB)
        com cálculo de cobertura potencial, relação habitantes/equipe e diagnóstico de déficit.
        """
        buffer = io.BytesIO()
        df = pd.DataFrame(panorama)

        cols_map = {
            'municipio': 'Município',
            'uf': 'UF',
            'populacao_usada': 'População Base (IBGE)',
            'pop_censo_2022': 'População Censo 2022',
            'pop_estimada': 'População Estimada',
            'total_equipes': 'Total de Equipes Cadastradas',
            'total_esf': 'Qtd ESF (Saúde da Família)',
            'total_eap': 'Qtd EAP (Atenção Primária)',
            'total_ab': 'Total Atenção Básica (ESF+EAP)',
            'total_esb': 'Qtd ESB (Saúde Bucal)',
            'total_emulti': 'Qtd EMULTI',
            'hab_por_esf': 'Habitantes por ESF',
            'hab_por_equipe_total': 'Habitantes por Equipe AB (ESF+EAP)',
            'hab_por_esb': 'Habitantes por Equipe Bucal',
            'cobertura_esf_pct': 'Cobertura Potencial ESF (%)',
            'cobertura_total_pct': 'Cobertura Potencial Total AB (%)',
            'cobertura_esb_pct': 'Cobertura Bucal (%)',
            'pop_coberta': 'População Coberta Estimada',
            'pop_descoberta': 'População Descoberta Estimada',
            'deficit_esf': 'Déficit Estimado de Equipes ESF',
            'diagnostico': 'Diagnóstico de Cobertura',
            'total_estabelecimentos': 'Unidades Básicas com Equipes',
            'competencia': 'Competência CNES'
        }

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            if not df.empty:
                present_cols = [c for c in cols_map.keys() if c in df.columns]
                df_export = df[present_cols].rename(columns=cols_map) if present_cols else df

                # Linha de Totais Regionais
                tot_dict = {
                    'Município': 'TOTAL REGIONAL (DRS VIII)',
                    'UF': 'SP',
                    'População Base (IBGE)': df['populacao_usada'].sum() if 'populacao_usada' in df.columns else 0,
                    'População Censo 2022': df['pop_censo_2022'].sum() if 'pop_censo_2022' in df.columns else 0,
                    'População Estimada': df['pop_estimada'].sum() if 'pop_estimada' in df.columns else 0,
                    'Total de Equipes Cadastradas': df['total_equipes'].sum() if 'total_equipes' in df.columns else 0,
                    'Qtd ESF (Saúde da Família)': df['total_esf'].sum() if 'total_esf' in df.columns else 0,
                    'Qtd EAP (Atenção Primária)': df['total_eap'].sum() if 'total_eap' in df.columns else 0,
                    'Total Atenção Básica (ESF+EAP)': df['total_ab'].sum() if 'total_ab' in df.columns else 0,
                    'Qtd ESB (Saúde Bucal)': df['total_esb'].sum() if 'total_esb' in df.columns else 0,
                    'Qtd EMULTI': df['total_emulti'].sum() if 'total_emulti' in df.columns else 0,
                    'População Coberta Estimada': df['pop_coberta'].sum() if 'pop_coberta' in df.columns else 0,
                    'População Descoberta Estimada': df['pop_descoberta'].sum() if 'pop_descoberta' in df.columns else 0,
                    'Déficit Estimado de Equipes ESF': df['deficit_esf'].sum() if 'deficit_esf' in df.columns else 0,
                    'Unidades Básicas com Equipes': df['total_estabelecimentos'].sum() if 'total_estabelecimentos' in df.columns else 0,
                    'Competência CNES': competencia
                }

                # Cálculo de médias ponderadas regionais
                pop_tot = tot_dict['População Base (IBGE)']
                esf_tot = tot_dict['Qtd ESF (Saúde da Família)']
                ab_tot = tot_dict['Total Atenção Básica (ESF+EAP)']
                esb_tot = tot_dict['Qtd ESB (Saúde Bucal)']

                tot_dict['Habitantes por ESF'] = round(pop_tot / esf_tot) if esf_tot > 0 else 0
                tot_dict['Habitantes por Equipe AB (ESF+EAP)'] = round(pop_tot / ab_tot) if ab_tot > 0 else 0
                tot_dict['Habitantes por Equipe Bucal'] = round(pop_tot / esb_tot) if esb_tot > 0 else 0
                tot_dict['Cobertura Potencial Total AB (%)'] = min(100.0, round((tot_dict['População Coberta Estimada'] / pop_tot) * 100, 1)) if pop_tot > 0 else 0
                tot_dict['Cobertura Potencial ESF (%)'] = min(100.0, round(((esf_tot * 3000) / pop_tot) * 100, 1)) if pop_tot > 0 else 0
                tot_dict['Cobertura Bucal (%)'] = min(100.0, round(((esb_tot * 3500) / pop_tot) * 100, 1)) if pop_tot > 0 else 0
                tot_dict['Diagnóstico de Cobertura'] = 'Panorama Regional Consolidado'

                df_tot = pd.DataFrame([tot_dict])
                df_final = pd.concat([df_export, df_tot], ignore_index=True)
                df_final.to_excel(writer, sheet_name="Panorama Regional Cobertura", index=False)
            else:
                pd.DataFrame({"Aviso": ["Nenhum dado regional encontrado."]}).to_excel(writer, sheet_name="Aviso", index=False)

        # Aplicar estilização visual padrão
        buffer.seek(0)
        wb = openpyxl.load_workbook(buffer)

        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.fill = cls.HEADER_FILL
                cell.font = cls.HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Linha de dados
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row - 1):
                for cell in row:
                    cell.font = cls.CELL_FONT
                    cell.border = cls.BORDER_THIN

            # Linha final de Total Regional em destaque
            if ws.max_row > 2:
                for cell in ws[ws.max_row]:
                    cell.font = Font(name="Segoe UI", size=10, bold=True, color="0F4C81")
                    cell.fill = PatternFill(start_color="EAF2F8", end_color="EAF2F8", fill_type="solid")
                    cell.border = cls.BORDER_THIN

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 40)

        output_buf = io.BytesIO()
        wb.save(output_buf)
        return output_buf.getvalue()



