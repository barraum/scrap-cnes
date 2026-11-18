import argparse
import sys
import os
from datetime import datetime

# Garantir UTF-8 no console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from cnes_core.client import CNESClient
from cnes_core.database import CNESDatabase
from cnes_core.exporter import CNESExporter

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Extrator & Gerenciador de Histórico do CNES (DATASUS)")
    parser.add_argument("--cnes", type=str, help="Código CNES (7 dígitos) ou ID do Estabelecimento (ex: 2705982)")
    parser.add_argument("--comp", type=str, help="Competência no formato YYYYMM (ex: 202607). Se omitido, busca a atual.")
    parser.add_argument("--export", action="store_true", help="Gera arquivo Excel (.xlsx) dos dados consultados.")
    parser.add_argument("--list", action="store_true", help="Lista todos os estabelecimentos cadastrados no histórico local.")
    parser.add_argument("--history", type=str, help="Exibe o histórico de competências salvas para um CNES.")
    parser.add_argument("--compare", nargs=3, metavar=('CNES', 'COMP_ANT', 'COMP_NOV'), help="Compara duas competências salvas.")

    args = parser.parse_args()

    # Diretório base dinâmico do projeto
    base_dir = os.path.dirname(os.path.abspath(__file__))

    db = CNESDatabase()
    client = CNESClient()

    # Opção: Listar estabelecimentos
    if args.list:
        estabelecimentos = db.list_estabelecimentos()
        if not estabelecimentos:
            console.print("[yellow]Nenhum estabelecimento salvo no histórico local ainda.[/yellow]")
            return

        table = Table(title="Estabelecimentos no Banco de Histórico Local", header_style="bold cyan")
        table.add_column("CNES", style="bold yellow")
        table.add_column("Nome Fantasia", style="white")
        table.add_column("Município / UF", style="dim")
        table.add_column("Total Comp.", justify="center")
        table.add_column("Última Atualização", style="dim")

        for e in estabelecimentos:
            table.add_row(
                e['cnes'],
                e['nome_fantasia'] or e['razao_social'] or '-',
                f"{e['municipio'] or '-'} / {e['uf'] or '-'}",
                str(e['total_competencias']),
                e['ultima_atualizacao'] or '-'
            )
        console.print(table)
        return

    # Opção: Ver Histórico
    if args.history:
        comps = db.list_competencias(args.history)
        if not comps:
            console.print(f"[yellow]Nenhum histórico encontrado para o CNES {args.history}.[/yellow]")
            return

        table = Table(title=f"Histórico de Competências Salvas - CNES {args.history}", header_style="bold green")
        table.add_column("Competência", style="bold yellow")
        table.add_column("Profissionais", justify="right")
        table.add_column("Leitos", justify="right")
        table.add_column("Equipamentos", justify="right")
        table.add_column("Serviços", justify="right")
        table.add_column("Data Extração", style="dim")

        for c in comps:
            table.add_row(
                c['competencia'],
                str(c['num_profissionais']),
                str(c['num_leitos']),
                str(c['num_equipamentos']),
                str(c['num_servicos']),
                c['data_extracao']
            )
        console.print(table)
        return

    # Opção: Comparar duas competências
    if args.compare:
        cnes, comp1, comp2 = args.compare
        res = db.compare_competencias(cnes, comp1, comp2)
        if "erro" in res:
            console.print(f"[bold red]Erro:[/bold red] {res['erro']}")
            return

        p = res['profissionais']
        l = res['leitos']
        
        diff_p_color = "green" if p['diferenca'] >= 0 else "red"
        diff_l_color = "green" if l['diferenca_existente'] >= 0 else "red"

        console.print(Panel.fit(
            f"[bold blue]Comparação de Evolução Histórica - CNES {cnes}[/bold blue]\n"
            f"Competência Anterior: [yellow]{comp1}[/yellow] -> Competência Nova: [yellow]{comp2}[/yellow]\n\n"
            f"• [bold]Profissionais:[/bold] {p['total_anterior']} -> {p['total_novo']} ([{diff_p_color}]{p['diferenca']:+d}[/{diff_p_color}])\n"
            f"  - Ingressos/Novos registrados: {len(p['novos_ingressos'])}\n"
            f"  - Desligados/Saídas: {len(p['desligados'])}\n\n"
            f"• [bold]Leitos Hospitalares (Existentes):[/bold] {l['total_existente_anterior']} -> {l['total_existente_novo']} ([{diff_l_color}]{l['diferenca_existente']:+d}[/{diff_l_color}])\n"
            f"• [bold]Leitos SUS:[/bold] {l['sus_anterior']} -> {l['sus_novo']} ({l['diferenca_sus']:+d})",
            title="Relatório de Mudanças"
        ))
        return

    # Consulta Padrão por CNES
    if not args.cnes:
        console.print("[bold cyan]Uso:[/bold cyan] python cnes_cli.py --cnes <CÓDIGO_CNES> [--comp YYYYMM] [--export]")
        console.print("Para ver opções completas: python cnes_cli.py --help")
        return

    cnes_input = args.cnes.strip()
    competencia = args.comp.strip() if args.comp else None

    console.print(f"\n[bold green]Iniciando extração inteligente CNES {cnes_input}...[/bold green]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Consultando microserviços do DATASUS...", total=None)
        try:
            full_data = client.fetch_full_establishment(cnes_input, competencia)
        except Exception as e:
            console.print(f"[bold red]Erro ao extrair dados:[/bold red] {e}")
            sys.exit(1)

    meta = full_data['metadata']
    prof_count = len(full_data.get('profissionais', []))
    leitos_count = sum(int(l.get('qtExistente', 0)) for l in full_data.get('leitos', []))
    leitos_sus = sum(int(l.get('qtSus', 0)) for l in full_data.get('leitos', []))
    equip_count = len(full_data.get('equipamentos', []))
    serv_count = len(full_data.get('servicos_classificacao', []))
    hab_count = len(full_data.get('habilitacoes', []))

    # Salva no banco de dados local
    ok, msg = db.save_snapshot(full_data)
    
    console.print(Panel(
        f"[bold white]{meta.get('nomeFantasia') or meta.get('razaoSocial')}[/bold white]\n"
        f"CNES: [yellow]{meta.get('cnes')}[/yellow] | ID: {meta.get('coUnidade')} | Competência: [cyan]{meta.get('competencia')}[/cyan]\n"
        f"Município: {meta.get('municipio')} - {meta.get('uf')}\n\n"
        f"Profissionais Ativos: [bold green]{prof_count}[/bold green]\n"
        f"Leitos Totais: [bold green]{leitos_count}[/bold green] (SUS: {leitos_sus})\n"
        f"Equipamentos: [bold green]{equip_count}[/bold green]\n"
        f"Serviços Especializados: [bold green]{serv_count}[/bold green]\n"
        f"Habilitações Ministeriais: [bold green]{hab_count}[/bold green]",
        title="[bold blue]Resumo do Estabelecimento[/bold blue]"
    ))

    console.print(f"[dim]{msg}[/dim]")

    # Exportar Excel se solicitado
    if args.export:
        out_filename = f"CNES_{meta.get('cnes')}_{meta.get('competencia') or 'atual'}.xlsx"
        out_path = os.path.join(base_dir, "output", out_filename)
        CNESExporter.export_to_excel(full_data, out_path)
        console.print(f"[bold green]✓ Relatório Excel gerado com sucesso:[/bold green] [underline]{out_path}[/underline]")

if __name__ == "__main__":
    main()
