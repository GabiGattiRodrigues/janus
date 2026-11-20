"""
Gera a base sintética do Janus.

Empresa fictícia: a Lumina, um app de conteúdo digital por assinatura que chega ao cliente
de dois jeitos -- por parceiros (operadora, banco, varejo, fintech), que pagam uma tarifa por
assinante ativo (B2B2C), e pela venda direta no app (B2C).

O que sai daqui:
- dados/realizado_mensal.csv : jan/2024 a out/2026, uma linha por parceiro e mês
- dados/plano_2026.csv       : as premissas do plano anual de 2026, feitas em dez/2025

A base é sintética de propósito: as premissas do plano são conhecidas e os desvios de 2026
foram plantados (ativação da Aurora caiu, churn do Varejo Delta piorou, Éter acima do plano,
CAC do canal direto subindo, reajuste de tarifa da Boreal). Assim dá pra conferir se a leitura
do mês e a ponte de variação encontram o que foi plantado.

Rodar: python dados/gerar_base.py
"""

import os

import numpy as np
import pandas as pd

PASTA = os.path.dirname(os.path.abspath(__file__))
SEMENTE = 20261120

MESES = pd.date_range("2024-01-01", "2026-10-01", freq="MS")

# ------------------------------------------------------------------ premissas verdadeiras
# elegivel: clientes do parceiro com acesso ao app (milhares); cresc: crescimento mensal da elegível
# ativ: % da elegível que ativa no mês; churn: % da base que cancela no mês
# tarifa: R$ que o parceiro paga por assinante ativo/mês; custo: R$ de conteúdo (royalties) por assinante ativo/mês
PARCEIROS = {
    "Operadora Aurora": dict(tipo="B2B2C", inicio="2024-01", elegivel=9000, cresc=0.002,
                             ativ=0.0085, churn=0.060, tarifa=3.20, custo=1.15),
    "Operadora Boreal": dict(tipo="B2B2C", inicio="2024-01", elegivel=6000, cresc=0.003,
                             ativ=0.0070, churn=0.072, tarifa=2.90, custo=1.05),
    "Banco Cerrado": dict(tipo="B2B2C", inicio="2024-01", elegivel=4000, cresc=0.004,
                          ativ=0.0050, churn=0.040, tarifa=4.50, custo=1.60),
    "Varejo Delta": dict(tipo="B2B2C", inicio="2024-01", elegivel=3000, cresc=0.001,
                         ativ=0.0060, churn=0.085, tarifa=2.40, custo=1.35),
    "Fintech Éter": dict(tipo="B2B2C", inicio="2025-03", elegivel=1500, cresc=0.025,
                         ativ=0.0120, churn=0.050, tarifa=3.80, custo=1.40),
}
# Canal direto: ativações vêm da verba de marketing (verba / CAC); preço líquido já sem a taxa da loja
DIRETO = dict(tipo="Direto", inicio="2024-01", verba=900, cac=42.0, churn=0.080, preco=21.00, custo=5.50)

CUSTO_FIXO = 5200  # R$ mil/mês: plataforma, time, catálogo (entra no resultado operacional)


def fator_sazonal(mes):
    """Ativação um pouco maior em janeiro (ano novo) e novembro (Black Friday), menor em junho."""
    return {1: 1.15, 6: 0.92, 11: 1.12, 12: 0.95}.get(mes, 1.0)


def desvio_2026(nome, data):
    """Os desvios plantados em 2026: o que o plano não previa."""
    d = dict(ativ=1.0, churn=1.0, tarifa=1.0, custo=1.0, cac=1.0)
    if data.year < 2026:
        return d
    m = data.month
    if nome == "Operadora Aurora" and m >= 4:        # parceiro escondeu o app no menu novo
        d["ativ"] = 0.72
    if nome == "Varejo Delta":                        # churn piorando mês a mês
        d["churn"] = 1.0 + 0.025 * m
    if nome == "Fintech Éter":                        # parceiro novo indo melhor que o plano
        d["ativ"] = 1.25
    if nome == "Operadora Boreal" and m >= 7:         # reajuste de tarifa que entrou no meio do ano
        d["tarifa"] = 1.08
    if nome.startswith("Direto"):                            # leilão de mídia mais caro
        d["cac"] = 1.0 + 0.03 * m
    return d


def simular_parceiro(nome, p, rng):
    """Mês a mês: base nova = base anterior + ativações - cancelamentos."""
    linhas = []
    elegivel = p.get("elegivel", 0.0)
    inicio = pd.Timestamp(p["inicio"] + "-01")
    maduro = inicio <= MESES[0]
    # parceiro que já existia em jan/2024 começa com a base no equilíbrio (entra = sai)
    if not maduro:
        base = 0.0
    elif p["tipo"] == "Direto":
        base = p["verba"] / p["cac"] / p["churn"]
    else:
        base = elegivel * p["ativ"] / p["churn"]
    for data in MESES:
        if data < inicio:
            continue
        dv = desvio_2026(nome, data)
        ruido = rng.normal(1.0, 0.06)
        if p["tipo"] == "Direto":
            verba = p["verba"] * fator_sazonal(data.month) * rng.normal(1.0, 0.05)
            cac = p["cac"] * dv["cac"] * rng.normal(1.0, 0.04)
            ativacoes = verba * 1000 / cac / 1000          # milhares de assinantes
            preco = p["preco"]
        else:
            elegivel = elegivel * (1 + p["cresc"])
            verba, cac = 0.0, np.nan
            taxa = p["ativ"] * dv["ativ"] * fator_sazonal(data.month) * ruido
            # parceiro novo: rampa nos 4 primeiros meses
            meses_vida = (data.year - inicio.year) * 12 + data.month - inicio.month
            if not maduro:
                taxa *= min(1.0, 0.4 + 0.15 * meses_vida)
            ativacoes = elegivel * taxa
            preco = p["tarifa"] * dv["tarifa"]
        churn = min(0.5, p["churn"] * dv["churn"] * rng.normal(1.0, 0.05))
        cancelamentos = base * churn
        base_ini = base
        base = base + ativacoes - cancelamentos
        custo_unit = p["custo"] * dv["custo"] * rng.normal(1.0, 0.02)
        linhas.append(dict(
            mes=data.strftime("%Y-%m-%d"), parceiro=nome, tipo=p["tipo"],
            elegivel_mil=round(elegivel, 1),
            base_inicial_mil=round(base_ini, 2), ativacoes_mil=round(ativacoes, 2),
            cancelamentos_mil=round(cancelamentos, 2), base_final_mil=round(base, 2),
            preco_unit=round(preco, 2), receita_mil=round(base * preco, 1),
            custo_conteudo_mil=round(base * custo_unit, 1),
            verba_mkt_mil=round(verba, 1),
        ))
    return linhas


def montar_plano(real):
    """
    Plano de 2026 feito em dez/2025, como um time de planejamento faria:
    taxas = média de jun a nov/2025 (com um pouco de ambição na ativação),
    tarifas e custos = contrato vigente, verba do direto = orçamento aprovado.
    """
    jan = real[(real.mes >= "2025-06-01") & (real.mes <= "2025-11-01")]
    linhas = []
    for nome, g in jan.groupby("parceiro"):
        p = PARCEIROS.get(nome, DIRETO)
        ult = real[(real.parceiro == nome) & (real.mes == "2025-12-01")].iloc[0]
        taxa_ativ = (g.ativacoes_mil / g.elegivel_mil.replace(0, np.nan)).mean() if p["tipo"] != "Direto" else np.nan
        linhas.append(dict(
            parceiro=nome, tipo=p["tipo"],
            base_dez25_mil=round(ult.base_final_mil, 2),
            elegivel_dez25_mil=round(ult.elegivel_mil, 1),
            cresc_elegivel_mes=p.get("cresc", 0.0),
            ativacao_mes=round(taxa_ativ * 1.03, 5) if p["tipo"] != "Direto" else np.nan,
            churn_mes=round((g.cancelamentos_mil / g.base_inicial_mil).mean(), 4),
            preco_unit=p.get("tarifa", p.get("preco")),
            custo_unit=p["custo"],
            verba_mkt_mes_mil=DIRETO["verba"] if p["tipo"] == "Direto" else 0.0,
            cac=round(DIRETO["cac"] * 1.02, 1) if p["tipo"] == "Direto" else np.nan,
        ))
    plano = pd.DataFrame(linhas)
    plano["custo_fixo_mes_mil"] = CUSTO_FIXO
    return plano


def main():
    rng = np.random.default_rng(SEMENTE)
    linhas = []
    for nome, p in PARCEIROS.items():
        linhas += simular_parceiro(nome, p, rng)
    linhas += simular_parceiro("Direto (app)", DIRETO, rng)
    real = pd.DataFrame(linhas)
    real["custo_fixo_mil"] = CUSTO_FIXO / real.groupby("mes").parceiro.transform("count")
    plano = montar_plano(real)
    real.to_csv(os.path.join(PASTA, "realizado_mensal.csv"), index=False)
    plano.to_csv(os.path.join(PASTA, "plano_2026.csv"), index=False)
    print(real.groupby("mes")[["base_final_mil", "receita_mil"]].sum().tail(14).round(0))
    print(plano.T)


if __name__ == "__main__":
    main()
