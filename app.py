"""Janus — plano, forecast, OKRs e business case de um negócio de assinatura B2B2C."""
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from janus import i18n
from janus import modelo as M
from janus.i18n import L

RAIZ = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="Janus · plano e forecast · planning & forecast",
                   page_icon=os.path.join(RAIZ, "assets", "janus_icone.png"), layout="wide")
i18n.iniciar()
EN = i18n.en()

# ------------------------------------------------------------------ paleta
AZUL = "#2a78d6"
AZUL_ESC = "#0e3f7a"
AZUL_CLARO = "#9cc2ee"
CINZA = "#8a8984"
VERDE = "#1baf7a"
VERMELHO = "#e34948"
AMARELO = "#eda100"
FAROL = {  # fundo, cor do texto, ícone
    "verde": ("#e5f4e4", "#1b7a3a", "🟢", L("No caminho", "On track")),
    "amarelo": ("#fdf3d7", "#8a6100", "🟡", L("Em risco", "At risk")),
    "vermelho": ("#fbebeb", "#a12a2a", "🔴", L("Fora do caminho", "Off track")),
    "cinza": ("#f0efec", "#52514e", "⚪", ""),
}

st.markdown("""
<style>
h1, h2, h3 { letter-spacing: -0.01em; }
.nota {font-size:0.9rem; color:#52514e;}
.caixa {background:#f3f7fc; border-left:4px solid #2a78d6; padding:12px 16px; border-radius:6px; margin:6px 0 14px;}
.kr {padding:12px 14px; border-radius:8px; margin-bottom:10px; min-height:150px;}
.kr .t {font-size:0.92rem; color:#1f1f1e; font-weight:600;}
.kr .m {font-size:0.8rem; color:#52514e; margin-top:2px;}
.kr .b {font-size:1.45rem; font-weight:700; margin:6px 0 2px;}
.kr .s {font-size:0.85rem; font-weight:600;}
.chk {font-size:0.85rem; line-height:1.6;}
@media (prefers-color-scheme: dark) {
  .caixa, .caixa * {color:#ffffff !important;}
  .caixa {background:#15212f;}
  .nota {color:#c3c2b7;}
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ língua e formatos
NOMES_EN = {"Operadora Aurora": "Aurora Telecom", "Operadora Boreal": "Boreal Telecom", "Banco Cerrado": "Cerrado Bank",
            "Varejo Delta": "Delta Retail", "Fintech Éter": "Éter Fintech", "Direto (app)": "Direct (app)"}
ALAV = {
    "elegivel": L("Clientes elegíveis", "Eligible customers"), "ativ": L("Ativação", "Activation"),
    "verba": L("Verba de marketing (direto)", "Marketing budget (direct)"), "cac": L("CAC (direto)", "CAC (direct)"),
    "churn": "Churn", "preco": L("Preço / tarifa", "Price / fee"), "custo": L("Custo de conteúdo", "Content cost"),
    "cresc": L("Crescimento da elegível", "Eligible base growth"), "fixo": L("Custo fixo", "Fixed cost"),
}


def minus(x):
    """Primeira letra minúscula no meio da frase, sem estragar sigla (CAC)."""
    return x if x[:3].isupper() else x[0].lower() + x[1:]


def V(p):
    return NOMES_EN.get(p, p) if EN else p


def br(v, casas=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return i18n.num(v, casas)


def din(v_mil, casas=1):
    """R$ em milhares → 'R$ 15,4 mi' / 'R$ 583 mil'."""
    if abs(v_mil) >= 1000:
        return f"R$ {br(v_mil / 1000, casas)}{L(' mi', 'M')}"
    return f"R$ {br(v_mil, 0)}{L(' mil', 'K')}"


def gente(v_mil):
    """Assinantes em milhares → '3,20 mi' / '583 mil'."""
    if abs(v_mil) >= 1000:
        return f"{br(v_mil / 1000, 2)}{L(' mi', 'M')}"
    return f"{br(v_mil, 0)}{L(' mil', 'K')}"


def pct(v, casas=1, sinal=False):
    s = br(abs(v) if sinal else v, casas) + "%"
    return (("+" if v >= 0 else "-") + s) if sinal else s   # hífen comum: o Streamlit lê o sinal pra pintar a seta


def mes_txt(m):
    m = pd.Timestamp(m)
    nomes = i18n.MESES_EN if EN else i18n.MESES_PT
    return f"{nomes[m.month - 1]}/{m.year}"


LAYOUT = dict(margin=dict(l=10, r=10, t=60, b=10), height=380, hovermode="closest",
              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
              legend=dict(orientation="h", yanchor="top", y=-0.15, x=0, font=dict(size=11)),
              font=dict(size=12), separators=".," if EN else ",.")
EIXO = dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False, linecolor="rgba(128,128,128,0.4)")


def lay(fig, titulo=None, **kw):
    fig.update_layout(**{**LAYOUT, **kw})
    if titulo:
        fig.update_layout(title=dict(text=titulo, x=0, xanchor="left", font=dict(size=14)))
    fig.update_xaxes(**EIXO)
    fig.update_yaxes(**EIXO)


def caixa(txt):
    st.markdown(f"<div class='caixa'>{txt}</div>", unsafe_allow_html=True)


def como_ler(txt, exemplo=None):
    """Explicação em linguagem simples + um exemplo com número do próprio app."""
    corpo = f"<b>{L('Como ler', 'How to read')}:</b> {txt}"
    if exemplo:
        corpo += f"<br><br><b>{L('Exemplo', 'Example')}:</b> {exemplo}"
    caixa(corpo)


# ------------------------------------------------------------------ dados e contas (cacheadas)
@st.cache_data
def carregar():
    real, plano = M.carregar()
    par = M.ordem_parceiros(real)
    saz = M.fatores_sazonais(real)
    return real, plano, par, saz


real, plano, PAR, SAZ = carregar()
ULT = real.mes.max()
CUSTO_FIXO = float(plano.custo_fixo_mes_mil.iloc[0])


@st.cache_data
def c_premissas(ate):
    return M.premissas_recentes(real, PAR, pd.Timestamp(ate), SAZ)


@st.cache_data
def c_plano():
    return M.plano_mensal_2026(real, plano, PAR, SAZ)


@st.cache_data
def c_ponte(ate):
    return M.ponte(real, plano, PAR, SAZ, pd.Timestamp(ate))


@st.cache_data
def c_sim(ate, h, mult_key=None, mult=None):
    prem = c_premissas(ate)
    return M.simular(real, prem, pd.Timestamp(ate), h, SAZ, mult=dict(mult) if mult else None)


@st.cache_data
def c_backtest():
    return M.backtest(real, PAR, SAZ)


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    i18n.seletor()
    st.image(os.path.join(RAIZ, "assets", "janus_capa.jpg"), width=180)
    st.markdown("### Janus")
    st.caption(L("O deus das duas faces: uma olha o que já aconteceu, a outra o que vem pela frente. "
                 "Plano, forecast, OKRs e business case num só lugar.",
                 "The two-faced god: one face looks at what already happened, the other at what's ahead. "
                 "Plan, forecast, OKRs and business case in one place."))
    st.divider()
    meses_2026 = list(pd.date_range("2026-01-01", ULT, freq="MS"))
    REF = st.select_slider(L("Mês de referência da leitura", "Reference month"), options=meses_2026,
                           value=ULT, format_func=mes_txt,
                           help=L("Até onde o realizado vai. A leitura do mês, a ponte e a aterrissagem do ano "
                                  "usam só o que se sabia até esse mês.",
                                  "How far the actuals go. The monthly review, the bridge and the year landing "
                                  "only use what was known up to this month."))
    st.divider()
    st.caption(L("Lumina é uma empresa fictícia e a base é sintética, com desvios plantados em 2026. "
                 "Projeto de portfólio de Gabriela Gatti Rodrigues.",
                 "Lumina is a fictional company and the data is synthetic, with deviations planted in 2026. "
                 "Portfolio project by Gabriela Gatti Rodrigues."))
    st.markdown("[gabigattirodrigues.github.io](https://gabigattirodrigues.github.io/)")

st.title("Janus")
st.markdown(L("**Plano, forecast, OKRs e business case** de um app de assinatura vendido por parceiros (B2B2C) e direto no app.",
              "**Plan, forecast, OKRs and business case** for a subscription app sold through partners (B2B2C) and directly in the app."))

abas = st.tabs([L("O case", "The case"), L("Leitura do mês", "Monthly review"), L("Plano e cenários", "Plan & scenarios"),
                L("Sensibilidade", "Sensitivity"), "OKRs", L("Parceiros", "Partners"), L("Novo país", "New country"),
                L("Como funciona", "How it works"), L("Glossário", "Glossary")])

# ================================================================== O CASE
with abas[0]:
    st.subheader(L("A pergunta", "The question"))
    caixa(L(
        "A <b>Lumina</b> é um app de conteúdo digital por assinatura. Ele chega ao cliente de dois jeitos: por "
        "<b>parceiros</b> (operadoras, banco, varejo, fintech), que pagam uma tarifa por assinante ativo, e pela "
        "<b>venda direta</b> no app. Todo fim de ano a empresa faz um plano; todo mês alguém precisa responder: "
        "<b>o plano continua de pé? O que precisa ser ajustado? Onde apostar agora?</b>",
        "<b>Lumina</b> is a digital-content subscription app. It reaches customers in two ways: through "
        "<b>partners</b> (telcos, a bank, a retailer, a fintech), which pay a fee per active subscriber, and through "
        "<b>direct sales</b> in the app. Every year-end the company builds a plan; every month someone has to answer: "
        "<b>is the plan still standing? What needs adjusting? Where should we bet now?</b>"))
    st.markdown(L("**O que cada aba responde**", "**What each tab answers**"))
    st.markdown(L(
        "| Aba | Pergunta |\n|---|---|\n"
        "| Leitura do mês | O plano continua de pé? De onde veio a diferença, por parceiro e por alavanca? |\n"
        "| Plano e cenários | Pra onde o negócio vai nos próximos 1 a 3 anos, em três cenários ou no seu? |\n"
        "| Sensibilidade | Qual alavanca mais mexe no resultado? |\n"
        "| OKRs | Os KRs estão bem escritos? Qual a chance de bater cada um? |\n"
        "| Parceiros | Quem dá dinheiro e quem só dá volume? Qual tarifa mínima faz sentido? |\n"
        "| Novo país | Vale abrir um mercado novo? Em quanto tempo se paga e com que chance? |",
        "| Tab | Question |\n|---|---|\n"
        "| Monthly review | Is the plan still standing? Where did the gap come from, by partner and by lever? |\n"
        "| Plan & scenarios | Where is the business going in the next 1–3 years, in three scenarios or in yours? |\n"
        "| Sensitivity | Which lever moves the result the most? |\n"
        "| OKRs | Are the KRs well written? What's the chance of hitting each one? |\n"
        "| Partners | Who brings money and who only brings volume? What minimum fee makes sense? |\n"
        "| New country | Is a new market worth it? How long until it pays back, and with what chance? |"))
    st.subheader(L("A conta por trás de tudo", "The math behind everything"))
    st.markdown(L("Uma árvore só, mês a mês e por parceiro. Plano, realizado, forecast e simulação mudam só as premissas que entram nela.",
                  "One single tree, month by month and per partner. Plan, actuals, forecast and simulation only change the assumptions that go into it."))
    r_ult = real[real.mes == ULT]
    st.graphviz_chart(f"""
digraph {{
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#e8f1fc", color="#2a78d6", fontname="Helvetica", fontsize=11];
  res [label="{L('Resultado operacional', 'Operating result')}\\n{din(r_ult.mc_mil.sum() - CUSTO_FIXO)}", fillcolor="#0e3f7a", fontcolor="white"];
  mc [label="{L('Margem de contribuição', 'Contribution margin')}\\n{din(r_ult.mc_mil.sum())}"];
  fixo [label="{L('Custo fixo', 'Fixed cost')}\\n{din(CUSTO_FIXO)}"];
  rec [label="{L('Receita', 'Revenue')}\\n{din(r_ult.receita_mil.sum())}"];
  cus [label="{L('Custo de conteúdo', 'Content cost')}\\n{din(r_ult.custo_conteudo_mil.sum())}"];
  ver [label="{L('Verba de marketing', 'Marketing budget')}\\n{din(r_ult.verba_mkt_mil.sum())}"];
  base [label="{L('Base ativa', 'Active base')}\\n{gente(r_ult.base_final_mil.sum())}"];
  pre [label="{L('Preço / tarifa', 'Price / fee')}"];
  cu [label="{L('Custo por assinante', 'Cost per subscriber')}"];
  ati [label="{L('Ativações', 'Activations')}\\n{gente(r_ult.ativacoes_mil.sum())}"];
  can [label="{L('Cancelamentos', 'Cancellations')}\\n{gente(r_ult.cancelamentos_mil.sum())}"];
  ele [label="{L('Elegíveis × taxa de ativação', 'Eligible × activation rate')}\\n(B2B2C)"];
  cac [label="{L('Verba ÷ CAC', 'Budget ÷ CAC')}\\n({L('direto', 'direct')})"];
  chu [label="{L('Base anterior × churn', 'Previous base × churn')}"];
  res -> mc [dir=back]; res -> fixo [dir=back, label=" −"]; mc -> rec [dir=back]; mc -> cus [dir=back, label=" −"]; mc -> ver [dir=back, label=" −"];
  rec -> base [dir=back]; rec -> pre [dir=back, label=" ×"]; cus -> cu [dir=back]; cus -> base [dir=back];
  base -> ati [dir=back, label=" +"]; base -> can [dir=back, label=" −"]; ati -> ele [dir=back]; ati -> cac [dir=back]; can -> chu [dir=back];
}}""", width="stretch")
    st.caption(L(f"Valores de {mes_txt(ULT)}, em reais e assinantes do mês.", f"Values for {mes_txt(ULT)}, in reais and subscribers for the month."))
    st.info(L("Base sintética e empresa fictícia. Os desvios de 2026 foram plantados de propósito (estão listados em "
              "Como funciona), pra dar pra conferir se a leitura do mês encontra o que aconteceu. Projeto autoral de "
              "portfólio: junta técnicas que uso no dia a dia (forecast, safras, simulação) num problema de planejamento.",
              "Synthetic data and a fictional company. The 2026 deviations were planted on purpose (listed in How it "
              "works), so you can check whether the monthly review finds what happened. An original portfolio project: "
              "it brings techniques I use day to day (forecasting, cohorts, simulation) into a planning problem."))

# ================================================================== LEITURA DO MÊS
with abas[1]:
    meses_pl, pl = c_plano()
    pecas, mc_plano_ytd, mc_real_ytd = c_ponte(REF)
    i_ref = list(meses_pl).index(pd.Timestamp(REF))
    r_mes = real[real.mes == REF]
    mc_mes, mc_mes_pl = r_mes.mc_mil.sum(), pl["mc"][:, i_ref].sum()
    base_mes, base_mes_pl = r_mes.base_final_mil.sum(), pl["base"][:, i_ref].sum()
    churn_mes = r_mes.cancelamentos_mil.sum() / r_mes.base_inicial_mil.sum() * 100
    resto = 12 - (i_ref + 1)
    plano_ano = pl["mc"].sum()
    if resto > 0:
        _, sim_ano = c_sim(REF, resto)
        aterr = mc_real_ytd + sim_ano["mc"].sum(axis=(1, 2))
    else:
        aterr = np.array([mc_real_ytd])
    chance_plano = float((aterr >= plano_ano).mean())

    st.subheader(L(f"Leitura de {mes_txt(REF)}", f"Review of {mes_txt(REF)}"))
    k = st.columns(4)
    k[0].metric(L("Margem de contribuição do mês", "Contribution margin, month"), din(mc_mes),
                pct((mc_mes / mc_mes_pl - 1) * 100, 1, True) + L(" vs plano", " vs plan"))
    k[1].metric(L("MC acumulada no ano", "Contribution margin, YTD"), din(mc_real_ytd),
                pct((mc_real_ytd / mc_plano_ytd - 1) * 100, 1, True) + L(" vs plano", " vs plan"))
    k[2].metric(L("Base ativa", "Active base"), gente(base_mes),
                pct((base_mes / base_mes_pl - 1) * 100, 1, True) + L(" vs plano", " vs plan"))
    k[3].metric(L("Churn do mês", "Churn, month"), pct(churn_mes, 2))

    # veredito
    if chance_plano >= 0.7:
        ver, cor_v = L("De pé", "Standing"), "verde"
    elif chance_plano >= 0.4:
        ver, cor_v = L("Em risco", "At risk"), "amarelo"
    else:
        ver, cor_v = L("Precisa de ajuste", "Needs adjusting"), "vermelho"
    fundo, cor_t, ic, _ = FAROL[cor_v]
    p50 = float(np.median(aterr))
    neg = pecas.groupby(["parceiro", "alavanca"]).efeito_mil.sum().sort_values()
    pos = neg[::-1]
    def frase(item):
        (p, a), v = item
        return f"{V(p)} · {ALAV[a]} ({'+' if v >= 0 else '−'}{din(abs(v))})"
    piores = [frase(x) for x in list(neg.items())[:2] if x[1] < 0]
    melhores = [frase(x) for x in list(pos.items())[:2] if x[1] > 0]
    st.markdown(
        f"<div class='kr' style='background:{fundo};border-left:6px solid {cor_t};min-height:0'>"
        f"<div class='t'>{L('O plano continua de pé?', 'Is the plan still standing?')}</div>"
        f"<div class='b' style='color:{cor_t}'>{ic} {ver} · {pct(chance_plano * 100, 0)} {L('de chance de bater o ano', 'chance of hitting the year')}</div>"
        f"<div class='m'>{L('Aterrissagem do ano (mediana)', 'Year landing (median)')}: <b>{din(p50)}</b> · "
        f"{L('plano', 'plan')}: <b>{din(plano_ano)}</b> · {L('diferença', 'gap')}: <b>{din(p50 - plano_ano)}</b></div>"
        f"<div class='m' style='margin-top:6px'>{L('Puxando pra baixo', 'Dragging down')}: {'; '.join(piores) or '–'}<br>"
        f"{L('Segurando', 'Holding up')}: {'; '.join(melhores) or '–'}</div></div>", unsafe_allow_html=True)

    ex_p, ex_a = neg.index[0]
    como_ler(
        L("o card responde à pergunta principal do mês. A <b>aterrissagem</b> é onde o ano deve fechar: o que já aconteceu "
          "até agora mais a previsão dos meses que faltam. A <b>chance de bater</b> vem de simular 600 vezes os meses que "
          "faltam, cada vez com um pouco mais ou menos de ativação, churn e CAC (do tamanho do que já variou no passado), "
          "e contar em quantas o ano fecha acima do plano.",
          "the card answers the month's main question. The <b>landing</b> is where the year should close: what already "
          "happened plus the forecast for the remaining months. The <b>chance of hitting</b> comes from simulating the remaining "
          "months 600 times, each with a bit more or less activation, churn and CAC (as much as they varied in the past), "
          "and counting in how many the year closes above plan."),
        L(f"se a chance é {pct(chance_plano * 100, 0)}, em {round(chance_plano * 600)} das 600 simulações o ano fecha acima "
          f"do plano. A maior perda até aqui é {V(ex_p)} em {minus(ALAV[ex_a])}: {din(abs(neg.iloc[0]))} a menos que o planejado.",
          f"if the chance is {pct(chance_plano * 100, 0)}, in {round(chance_plano * 600)} of the 600 simulations the year closes "
          f"above plan. The biggest loss so far is {V(ex_p)} on {minus(ALAV[ex_a])}: {din(abs(neg.iloc[0]))} below plan."))

    c1, c2 = st.columns([1.1, 1])
    with c1:
        ordem = ["elegivel", "ativ", "verba", "cac", "churn", "preco", "custo"]
        p = pecas.groupby("alavanca").efeito_mil.sum().reindex(ordem)
        p = p[p.abs() > 0.5]
        fig = go.Figure(go.Waterfall(
            x=[L("Plano", "Plan")] + [ALAV[a] for a in p.index] + [L("Realizado", "Actual")],
            measure=["absolute"] + ["relative"] * len(p) + ["total"],
            y=[mc_plano_ytd] + list(p.values) + [mc_real_ytd],
            text=[din(mc_plano_ytd)] + [("+" if v >= 0 else "−") + din(abs(v)) for v in p.values] + [din(mc_real_ytd)],
            textposition="outside", cliponaxis=False,
            increasing=dict(marker=dict(color=VERDE)), decreasing=dict(marker=dict(color=VERMELHO)),
            totals=dict(marker=dict(color=AZUL_ESC)), connector=dict(line=dict(color="rgba(128,128,128,0.4)")),
            hovertemplate="%{x}<br>%{text}<extra></extra>"))
        lo = min(mc_plano_ytd, mc_real_ytd) - p.abs().sum() * 0.8
        hi = max(mc_plano_ytd, mc_real_ytd) + p.abs().sum() * 0.6
        lay(fig, L(f"<b>Ponte da margem</b> · jan a {mes_txt(REF)}, plano → realizado",
                   f"<b>Margin bridge</b> · Jan to {mes_txt(REF)}, plan → actual"), height=420)
        fig.update_yaxes(range=[lo, hi], title=L("R$ mil", "R$ K"))
        st.plotly_chart(fig, width="stretch")
    with c2:
        pv = pecas.pivot_table(index="parceiro", columns="alavanca", values="efeito_mil", aggfunc="sum")
        pv = pv.reindex(index=PAR, columns=[a for a in ordem if a in pv.columns])
        pv = pv.loc[:, pv.abs().max() > 0.5]
        z = pv.values
        lim = np.abs(z).max()
        fig = go.Figure(go.Heatmap(
            z=z, x=[ALAV[c] for c in pv.columns], y=[V(i) for i in pv.index], zmin=-lim, zmax=lim,
            colorscale=[[0, VERMELHO], [0.5, "#ffffff"], [1, AZUL]], showscale=False,
            text=np.vectorize(lambda v: ("+" if v >= 0 else "−") + din(abs(v)))(z), texttemplate="%{text}",
            hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>"))
        lay(fig, L("<b>De onde veio a diferença</b> · parceiro × alavanca", "<b>Where the gap came from</b> · partner × lever"), height=420)
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(showgrid=False, tickangle=-30)
        st.plotly_chart(fig, width="stretch")
    como_ler(
        L("a <b>ponte</b> (à esquerda) começa na margem que o plano prometia e termina na que aconteceu. Cada barra no meio "
          "é uma alavanca: <span style='color:#1b7a3a'><b>verde</b></span> trouxe dinheiro a mais que o plano, "
          "<span style='color:#a12a2a'><b>vermelho</b></span> tirou. O <b>mapa</b> (à direita) abre a mesma conta por parceiro: "
          "quanto mais forte a cor, maior o efeito; vermelho tirou, azul trouxe. A soma das peças fecha exatamente a diferença.",
          "the <b>bridge</b> (left) starts at the margin the plan promised and ends at what happened. Each bar in between is a "
          "lever: <span style='color:#1b7a3a'><b>green</b></span> brought more money than plan, "
          "<span style='color:#a12a2a'><b>red</b></span> took it away. The <b>map</b> (right) opens the same math by partner: the "
          "stronger the color, the bigger the effect; red took, blue brought. The pieces add up exactly to the gap."),
        L(f"a barra de {ALAV['cac']} mostra {('+' if p.get('cac', 0) >= 0 else '−')}{din(abs(p.get('cac', 0)))}: com o mesmo dinheiro de "
          f"marketing, o app trouxe menos assinantes do que o plano esperava, porque cada um ficou mais caro.",
          f"the {ALAV['cac']} bar shows {('+' if p.get('cac', 0) >= 0 else '−')}{din(abs(p.get('cac', 0)))}: with the same marketing "
          f"money, the app brought fewer subscribers than planned, because each one got more expensive."))

    # mensal: plano x realizado x aterrissagem
    hist = real[real.mes >= "2026-01-01"].groupby("mes").mc_mil.sum()
    hist = hist[hist.index <= REF]
    fig = go.Figure()
    fig.add_bar(x=meses_pl, y=pl["mc"].sum(axis=0), name=L("Plano", "Plan"), marker_color="rgba(138,137,132,0.35)",
                hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra></extra>")
    fig.add_scatter(x=hist.index, y=hist.values, name=L("Realizado", "Actual"), mode="lines+markers",
                    line=dict(color=AZUL_ESC, width=3), hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra></extra>")
    if resto > 0:
        mf = pd.date_range(pd.Timestamp(REF) + pd.DateOffset(months=1), periods=resto, freq="MS")
        tot = sim_ano["mc"].sum(axis=1)
        fig.add_scatter(x=list(mf) + list(mf[::-1]), y=list(np.percentile(tot, 90, axis=0)) + list(np.percentile(tot, 10, axis=0)[::-1]),
                        fill="toself", fillcolor="rgba(42,120,214,0.15)", line=dict(width=0), name=L("Faixa provável (P10–P90)", "Likely range (P10–P90)"),
                        hoverinfo="skip")
        fig.add_scatter(x=mf, y=np.median(tot, axis=0), name=L("Forecast (mediana)", "Forecast (median)"),
                        line=dict(color=AZUL, dash="dot", width=2.5), hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra></extra>")
    lay(fig, L("<b>Margem de contribuição por mês em 2026</b> · R$ mil", "<b>Monthly contribution margin, 2026</b> · R$ K"), height=360)
    st.plotly_chart(fig, width="stretch")
    st.caption(L("Barras cinza = plano de cada mês. Linha azul-escura = o que aconteceu. Linha pontilhada = previsão dos meses "
                 "que faltam, com a faixa azul-clara mostrando onde o resultado deve cair em 8 de cada 10 simulações.",
                 "Grey bars = each month's plan. Dark-blue line = what happened. Dotted line = forecast for the remaining months, "
                 "with the light-blue band showing where the result should land in 8 out of 10 simulations."))

    with st.expander(L("O que ajustar (sugestões a partir da ponte)", "What to adjust (suggestions from the bridge)")):
        dicas = {
            "ativ": L("ativação abaixo do plano: entender com o parceiro o que mudou na jornada (app, menu, oferta) e rever a meta de ativação do resto do ano",
                      "activation below plan: understand with the partner what changed in the journey (app, menu, offer) and revise the activation target"),
            "cac": L("CAC subindo: rever mix de mídia e se a verba do direto ainda se paga; considerar mover verba pros parceiros",
                     "CAC rising: review the media mix and whether the direct budget still pays back; consider moving budget to partners"),
            "churn": L("churn acima do plano: olhar a safra que está cancelando e testar ações de retenção com grupo controle",
                       "churn above plan: look at which cohort is cancelling and test retention actions with a control group"),
            "preco": L("preço/tarifa diferente do plano: atualizar o contrato no plano do resto do ano",
                       "price/fee different from plan: update the contract in the rest-of-year plan"),
            "custo": L("custo de conteúdo acima do plano: revisar royalties por título mais lido", "content cost above plan: review royalties on the most-read titles"),
            "verba": L("verba gasta diferente do orçado: alinhar com marketing", "budget spent differs from plan: align with marketing"),
            "elegivel": L("base elegível diferente da combinada: confirmar com o parceiro", "eligible base differs from agreed: confirm with the partner"),
        }
        for (p_, a_), v_ in list(neg.items())[:4]:
            if v_ < 0:
                st.markdown(f"- **{V(p_)}** ({'−'}{din(abs(v_))}): {dicas[a_]}")

# ================================================================== PLANO E CENÁRIOS
with abas[2]:
    st.subheader(L("Pra onde o negócio vai", "Where the business is going"))
    c = st.columns([1, 1, 2])
    horiz = c[0].select_slider(L("Horizonte", "Horizon"), options=[12, 24, 36], value=24,
                               format_func=lambda x: L(f"{x} meses", f"{x} months"))
    metrica = c[1].selectbox(L("Métrica", "Metric"), ["mc", "resultado", "receita", "base"],
                             format_func=lambda x: {"mc": L("Margem de contribuição", "Contribution margin"),
                                                    "resultado": L("Resultado operacional", "Operating result"),
                                                    "receita": L("Receita", "Revenue"), "base": L("Base ativa", "Active base")}[x])
    with c[2]:
        st.markdown(L("**Seu cenário** (ajuste sobre as premissas recentes)", "**Your scenario** (adjusts the recent assumptions)"))
        s = st.columns(4)
        m_ativ = s[0].slider(L("Ativação", "Activation"), -30, 30, 0, 5, format="%d%%")
        m_churn = s[1].slider("Churn", -30, 30, 0, 5, format="%d%%")
        m_cac = s[2].slider("CAC", -30, 30, 0, 5, format="%d%%")
        m_reaj = s[3].slider(L("Reajuste/ano", "Price incr./yr"), 0, 10, 0, 1, format="%d%%")
    prem = c_premissas(ULT)
    meu = dict(ativ=1 + m_ativ / 100, churn=1 + m_churn / 100, cac=1 + m_cac / 100, custo=1.0, verba=1.0,
               reajuste=m_reaj / 100, cresc=1.0)

    def serie(out, meses):
        if metrica == "base":
            return out["base"].sum(axis=0)
        if metrica == "resultado":
            return out["mc"].sum(axis=0) - CUSTO_FIXO
        return out[metrica if metrica != "mc" else "mc"].sum(axis=0)

    hist = real.groupby("mes").agg(mc=("mc_mil", "sum"), receita=("receita_mil", "sum"), base=("base_final_mil", "sum"))
    hist["resultado"] = hist.mc - CUSTO_FIXO
    fig = go.Figure()
    fig.add_scatter(x=hist.index, y=hist[metrica], name=L("Realizado", "Actual"), line=dict(color=AZUL_ESC, width=2.5))
    mf, simf = c_sim(ULT, horiz)
    if metrica == "base":
        tot = simf["base"].sum(axis=1)
    elif metrica == "resultado":
        tot = simf["mc"].sum(axis=1) - CUSTO_FIXO
    else:
        tot = simf[metrica].sum(axis=1)
    fig.add_scatter(x=list(mf) + list(mf[::-1]), y=list(np.percentile(tot, 90, axis=0)) + list(np.percentile(tot, 10, axis=0)[::-1]),
                    fill="toself", fillcolor="rgba(42,120,214,0.13)", line=dict(width=0),
                    name=L("Faixa provável do cenário base (P10–P90)", "Base-case likely range (P10–P90)"), hoverinfo="skip")
    tabela = []
    cens = [("otimista", L("Otimista", "Optimistic"), VERDE, "dot", M.CENARIOS["otimista"]),
            ("base", L("Base", "Base"), AZUL, "solid", M.CENARIOS["base"]),
            ("pessimista", L("Pessimista", "Pessimistic"), VERMELHO, "dot", M.CENARIOS["pessimista"]),
            ("meu", L("Seu cenário", "Your scenario"), AMARELO, "dash", meu)]
    for chave, nome_c, cor, traco, mult in cens:
        mm, out = M.forecast(real, prem, ULT, horiz, SAZ, mult)
        fig.add_scatter(x=mm, y=serie(out, mm), name=nome_c, line=dict(color=cor, dash=traco, width=2.2 if chave != "meu" else 3))
        anos = pd.Series(mm.year)
        for ano in sorted(anos.unique()):
            idx = np.where(anos == ano)[0]
            tabela.append({L("Cenário", "Scenario"): nome_c, L("Ano", "Year"): str(ano),
                           L("Receita", "Revenue"): din(out["receita"][:, idx].sum()),
                           L("Margem de contribuição", "Contribution margin"): din(out["mc"][:, idx].sum()),
                           L("Resultado operacional", "Operating result"): din(out["mc"][:, idx].sum() - CUSTO_FIXO * len(idx)),
                           L("Base no fim do ano", "Year-end base"): gente(out["base"][:, idx[-1]].sum())})
    lay(fig, L("<b>Realizado e forecast por cenário</b>", "<b>Actuals and forecast by scenario</b>"), height=440)
    fig.update_yaxes(title=L("mil assinantes", "K subscribers") if metrica == "base" else L("R$ mil", "R$ K"))
    st.plotly_chart(fig, width="stretch")
    como_ler(
        L("a linha azul-escura é o que já aconteceu. Daí pra frente, cada linha é um <b>cenário</b>: um jeito diferente de o "
          "futuro andar. O <b>base</b> segue o ritmo dos últimos meses; o <b>otimista</b> e o <b>pessimista</b> mexem em "
          "ativação, churn e CAC pra cima ou pra baixo; o <b>seu cenário</b> (amarelo) é o que você montar nos controles acima. "
          "A faixa azul-clara mostra onde o cenário base deve cair em 8 de cada 10 simulações: quanto mais longe no tempo, "
          "mais larga ela fica, porque mais coisa pode mudar.",
          "the dark-blue line is what already happened. From there on, each line is a <b>scenario</b>: a different way the "
          "future could go. <b>Base</b> follows the pace of recent months; <b>optimistic</b> and <b>pessimistic</b> move activation, "
          "churn and CAC up or down; <b>your scenario</b> (yellow) is what you set in the controls above. The light-blue band "
          "shows where the base case should land in 8 out of 10 simulations: the further out, the wider it gets, because more can change."),
        L("coloque o churn em −10% no seu cenário e veja a linha amarela descolar da azul: é quanto valeria um "
          "programa de retenção que segurasse 1 em cada 10 cancelamentos.",
          "set churn to −10% in your scenario and watch the yellow line pull away from the blue one: that's what a "
          "retention program saving 1 in 10 cancellations would be worth."))
    st.dataframe(pd.DataFrame(tabela), hide_index=True, width="stretch")
    with st.expander(L("Premissas recentes de cada parceiro (ponto de partida do forecast)", "Recent assumptions per partner (forecast starting point)")):
        t = prem.copy()
        mostra = pd.DataFrame({
            L("Parceiro", "Partner"): [V(p) for p in t.index],
            L("Ativação/mês", "Activation/mo"): [pct(v * 100, 2) if not d else "–" for v, d in zip(t.ativ, t.direto)],
            L("Verba/mês", "Budget/mo"): [din(v) if d else "–" for v, d in zip(t.verba, t.direto)],
            "CAC": [f"R$ {br(v, 1)}" if d else "–" for v, d in zip(t.cac, t.direto)],
            L("Churn/mês", "Churn/mo"): [pct(v * 100, 2) for v in t.churn],
            L("Preço", "Price"): [f"R$ {br(v, 2)}" for v in t.preco],
            L("Custo/assinante", "Cost/subscriber"): [f"R$ {br(v, 2)}" for v in t.custo],
        })
        st.dataframe(mostra, hide_index=True, width="stretch")
        st.caption(L("Média dos últimos 12 meses com peso maior pros mais recentes (o peso cai pela metade a cada 3 meses); "
                     "a ativação vem sem sazonalidade e a sazonalidade é recolocada mês a mês no forecast.",
                     "Average of the last 12 months, weighting recent months more (weight halves every 3 months); "
                     "activation is deseasonalized and seasonality is put back month by month in the forecast."))
    st.caption(L("Cenários: otimista = +10% ativação, −8% churn, −5% CAC, reajuste de 4%/ano; pessimista = −12% ativação, "
                 "+10% churn, +12% CAC, sem reajuste. A faixa azul vem de 600 simulações do cenário base.",
                 "Scenarios: optimistic = +10% activation, −8% churn, −5% CAC, 4%/yr price increase; pessimistic = −12% "
                 "activation, +10% churn, +12% CAC, no increase. The blue band comes from 600 simulations of the base case."))

# ================================================================== SENSIBILIDADE
with abas[3]:
    st.subheader(L("Qual alavanca mais mexe no resultado", "Which lever moves the result the most"))
    choque = st.select_slider(L("Tamanho do choque em cada alavanca", "Shock size on each lever"), options=[5, 10, 20], value=10,
                              format_func=lambda x: f"±{x}%")
    sens, ref = M.sensibilidade(real, c_premissas(ULT), ULT, SAZ, 12, choque / 100, CUSTO_FIXO)
    fig = go.Figure()
    fig.add_bar(y=[ALAV[a] for a in sens.alavanca], x=sens.menos, orientation="h", name=L(f"Alavanca −{choque}%", f"Lever −{choque}%"),
                marker_color=AZUL_CLARO, hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>")
    fig.add_bar(y=[ALAV[a] for a in sens.alavanca], x=sens.mais, orientation="h", name=L(f"Alavanca +{choque}%", f"Lever +{choque}%"),
                marker_color=AZUL_ESC, hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>")
    lay(fig, L(f"<b>Mudança no resultado operacional dos próximos 12 meses</b> · hoje: {din(ref)}",
               f"<b>Change in operating result over the next 12 months</b> · today: {din(ref)}"), barmode="overlay", height=430)
    fig.update_xaxes(title=L("R$ mil", "R$ K"), zeroline=True, zerolinecolor="rgba(128,128,128,0.6)")
    st.plotly_chart(fig, width="stretch")
    s_i = sens.set_index("alavanca")
    caixa(L(
        f"<b>Como ler:</b> cada barra mostra quanto o resultado dos próximos 12 meses muda se só aquela alavanca andar {choque}%. "
        f"Preço é a que mais pesa ({din(abs(s_i.loc['preco','mais']))}), porque mexe na receita inteira. "
        f"Entre as que o time de negócio controla no dia a dia, <b>churn pesa mais que ativação</b>: "
        f"{choque}% a menos de churn vale {din(abs(s_i.loc['churn','menos']))}, contra {din(abs(s_i.loc['ativ','mais']))} de {choque}% a mais de ativação. "
        f"Ou seja, segurar quem já está na base rende mais do que trazer gente nova.<br><br><b>Exemplo:</b> hoje o churn médio é "
        f"{pct(c_premissas(ULT).churn.mean() * 100, 1)} ao mês. Cair {choque}% seria ir pra uns {pct(c_premissas(ULT).churn.mean() * 100 * (1 - choque / 100), 1)}: "
        f"parece pouco, mas são {din(abs(s_i.loc['churn','menos']))} a mais no ano.",
        f"<b>How to read:</b> each bar shows how much the next 12 months' result changes if only that lever moves {choque}%. "
        f"Price weighs the most ({din(abs(s_i.loc['preco','mais']))}), because it hits all revenue. "
        f"Among the levers the business team controls day to day, <b>churn weighs more than activation</b>: "
        f"{choque}% less churn is worth {din(abs(s_i.loc['churn','menos']))}, versus {din(abs(s_i.loc['ativ','mais']))} for {choque}% more activation. "
        f"In other words, keeping who is already in the base pays more than bringing new people in.<br><br><b>Example:</b> average churn "
        f"today is {pct(c_premissas(ULT).churn.mean() * 100, 1)} a month. A {choque}% drop takes it to about {pct(c_premissas(ULT).churn.mean() * 100 * (1 - choque / 100), 1)}: "
        f"it looks small, but it's {din(abs(s_i.loc['churn','menos']))} more in the year."))

# ================================================================== OKRs
with abas[4]:
    st.subheader(L("OKRs do 4º trimestre de 2026", "Q4 2026 OKRs"))
    st.markdown(L(f"Chance de bater cada KR com o realizado até {mes_txt(ULT)} e 600 simulações de nov e dez. Mude as metas e veja o farol mudar.",
                  f"Chance of hitting each KR using actuals up to {mes_txt(ULT)} and 600 simulations of Nov and Dec. Change the targets and watch the light change."))
    como_ler(
        L("um <b>OKR</b> é um objetivo (aonde a empresa quer chegar) com alguns <b>KRs</b> (números que mostram se chegou). "
          "Cada card é um KR. A <b>chance</b> responde: se o negócio seguir no ritmo de agora, com as variações normais, "
          "em quantas de 600 simulações de novembro e dezembro a meta é batida? O farol resume: "
          "<b>verde</b> = 70% ou mais (no caminho), <b>amarelo</b> = 40% a 70% (em risco, vale agir), "
          "<b>vermelho</b> = menos de 40% (fora do caminho: ou muda a ação, ou muda a meta). "
          "Os cards cinza são KRs que não dá pra projetar: um mal escrito e um que é marco (sim/não).",
          "an <b>OKR</b> is an objective (where the company wants to go) with a few <b>KRs</b> (numbers that show whether it got there). "
          "Each card is a KR. The <b>chance</b> answers: if the business keeps its current pace, with normal variation, in how many of "
          "600 simulations of November and December is the target hit? The light sums it up: <b>green</b> = 70%+ (on track), "
          "<b>yellow</b> = 40–70% (at risk, worth acting), <b>red</b> = under 40% (off track: change the action or the target). "
          "Grey cards are KRs that can't be projected: one poorly written and one milestone (yes/no)."),
        L("o KR de CAC do canal direto está vermelho porque o CAC vem subindo todo mês. Abra <b>Editar metas</b>, troque a meta de "
          "R$ 48 pra R$ 52 e veja o card mudar de cor: a pergunta passa a ser se a meta era realista, não só se o time vai bater.",
          "the direct-channel CAC KR is red because CAC has been rising every month. Open <b>Edit targets</b>, change the target from "
          "R$ 48 to R$ 52 and watch the card change color: the question becomes whether the target was realistic, not just whether the team will hit it."))
    _, sq = c_sim(ULT, 2)
    out_ = real[real.mes == "2026-10-01"]
    i_dir, i_del = PAR.index(M.DIRETO), PAR.index("Varejo Delta")
    with st.expander(L("Editar metas", "Edit targets"), expanded=False):
        e = st.columns(5)
        meta_base = e[0].number_input(L("Base em dez (mil)", "Dec base (K)"), value=3240, step=10)
        meta_churn = e[1].number_input(L("Churn Q4 máx. (%)", "Max Q4 churn (%)"), value=6.2, step=0.1, format="%.1f")
        meta_mc = e[2].number_input(L("MC Q4 mín. (R$ mil)", "Min Q4 margin (R$ K)"), value=28500, step=100)
        meta_cac = e[3].number_input(L("CAC dez máx. (R$)", "Max Dec CAC (R$)"), value=48.0, step=1.0)
        meta_del = e[4].number_input(L("Churn Delta dez máx. (%)", "Max Delta Dec churn (%)"), value=9.5, step=0.1, format="%.1f")
    churn_q4 = (out_.cancelamentos_mil.sum() + sq["cancelamentos"].sum(axis=(1, 2))) / \
               (out_.base_inicial_mil.sum() + out_.base_final_mil.sum() + sq["base"][:, :, 0].sum(axis=1)) * 100
    krs = [
        dict(obj=L("O1 · Crescer a base com rentabilidade", "O1 · Grow the base profitably"),
             kr=L(f"Base ativa em dez/2026 ≥ {gente(meta_base)}", f"Active base in Dec/2026 ≥ {gente(meta_base)}"),
             v=sq["base"][:, :, -1].sum(axis=1), meta=meta_base, maior=True, fmt=gente,
             base_ref=real[real.mes == "2026-09-01"].base_final_mil.sum(), alav=L("ativação, churn", "activation, churn"),
             dono=L("Head de Parcerias", "Head of Partnerships"), fonte=L("base de assinantes (fechamento do mês)", "subscriber base (month close)")),
        dict(obj=L("O1 · Crescer a base com rentabilidade", "O1 · Grow the base profitably"),
             kr=L(f"Churn médio do Q4 ≤ {pct(meta_churn)}", f"Average Q4 churn ≤ {pct(meta_churn)}"),
             v=churn_q4, meta=meta_churn, maior=False, fmt=lambda x: pct(x, 2),
             base_ref=6.3, alav="churn", dono=L("Head de CRM", "Head of CRM"), fonte=L("cancelamentos ÷ base do início do mês", "cancellations ÷ start-of-month base")),
        dict(obj=L("O1 · Crescer a base com rentabilidade", "O1 · Grow the base profitably"),
             kr=L(f"Margem de contribuição do Q4 ≥ {din(meta_mc)}", f"Q4 contribution margin ≥ {din(meta_mc)}"),
             v=out_.mc_mil.sum() + sq["mc"].sum(axis=(1, 2)), meta=meta_mc, maior=True, fmt=din,
             base_ref=real[(real.mes >= "2026-07-01") & (real.mes <= "2026-09-01")].mc_mil.sum(),
             alav=L("todas", "all"), dono="CFO", fonte=L("DRE gerencial", "management P&L")),
        dict(obj=L("O2 · Fazer o canal direto se pagar", "O2 · Make the direct channel pay off"),
             kr=L(f"CAC do canal direto em dez ≤ R$ {br(meta_cac)}", f"Direct-channel CAC in Dec ≤ R$ {br(meta_cac)}"),
             v=sq["cac"][:, i_dir, -1], meta=meta_cac, maior=False, fmt=lambda x: f"R$ {br(x, 1)}",
             base_ref=real[(real.parceiro == M.DIRETO) & (real.mes == "2026-09-01")].eval("verba_mkt_mil / ativacoes_mil").iloc[0],
             alav="CAC", dono=L("Head de Growth", "Head of Growth"), fonte=L("verba de mídia ÷ assinaturas no app", "media spend ÷ in-app subscriptions")),
        dict(obj=L("O3 · Arrumar a carteira de parceiros", "O3 · Fix the partner portfolio"),
             kr=L(f"Churn do Varejo Delta em dez ≤ {pct(meta_del)}", f"Delta Retail churn in Dec ≤ {pct(meta_del)}"),
             v=sq["cancelamentos"][:, i_del, -1] / sq["base"][:, i_del, -2] * 100, meta=meta_del, maior=False, fmt=lambda x: pct(x, 2),
             base_ref=real[(real.parceiro == "Varejo Delta") & (real.mes == "2026-09-01")].eval("cancelamentos_mil / base_inicial_mil * 100").iloc[0],
             alav="churn", dono=L("Gerente da conta Delta", "Delta account manager"), fonte=L("base de assinantes do parceiro", "partner subscriber base")),
    ]
    ruins = [
        dict(obj=L("O2 · Fazer o canal direto se pagar", "O2 · Make the direct channel pay off"),
             kr=L("Melhorar o engajamento dos usuários", "Improve user engagement"), tipo="mal"),
        dict(obj=L("O3 · Arrumar a carteira de parceiros", "O3 · Fix the partner portfolio"),
             kr=L("Fechar contrato com 1 parceiro novo até dez", "Sign 1 new partner by Dec"), tipo="manual"),
    ]

    def farol(pr):
        return "verde" if pr >= 0.7 else ("amarelo" if pr >= 0.4 else "vermelho")

    cols = st.columns(3)
    for n_, k_ in enumerate(krs):
        ok = (k_["v"] >= k_["meta"]) if k_["maior"] else (k_["v"] <= k_["meta"])
        pr = float(ok.mean())
        fundo, cor_t, ic, rot = FAROL[farol(pr)]
        with cols[n_ % 3]:
            st.markdown(
                f"<div class='kr' style='background:{fundo};border-left:6px solid {cor_t}'>"
                f"<div class='m'>{k_['obj']}</div><div class='t'>{k_['kr']}</div>"
                f"<div class='b' style='color:{cor_t}'>{pct(pr * 100, 0)} {L('de chance', 'chance')}</div>"
                f"<div class='s' style='color:{cor_t}'>{ic} {rot}</div>"
                f"<div class='m'>{L('Projeção (mediana)', 'Projection (median)')}: {k_['fmt'](float(np.median(k_['v'])))} · "
                f"{L('linha de base (set)', 'baseline (Sep)')}: {k_['fmt'](k_['base_ref'])}</div></div>", unsafe_allow_html=True)
    for n_, k_ in enumerate(ruins, start=len(krs)):
        fundo, cor_t, _, _ = FAROL["cinza"]
        if k_["tipo"] == "mal":
            grande, sub = L("⚠️ KR mal definido", "⚠️ Poorly defined KR"), L("sem métrica, linha de base, meta nem fonte: não dá pra saber se bateu", "no metric, baseline, target or source: no way to tell if it was hit")
        else:
            grande, sub = L("✋ Sem projeção", "✋ No projection"), L("é um marco (sim/não), não sai dos dados: acompanhamento manual", "a milestone (yes/no), not from data: tracked manually")
        with cols[n_ % 3]:
            st.markdown(f"<div class='kr' style='background:{fundo};border-left:6px solid {cor_t}'>"
                        f"<div class='m'>{k_['obj']}</div><div class='t'>{k_['kr']}</div>"
                        f"<div class='b' style='color:{cor_t};font-size:1.2rem'>{grande}</div>"
                        f"<div class='m'>{sub}</div></div>", unsafe_allow_html=True)

    st.markdown(L("#### O KR está bem escrito?", "#### Is the KR well written?"))
    st.caption(L("Checklist de cada KR: sem esses seis itens, ninguém consegue dizer se bateu.",
                 "Checklist for each KR: without these six items, no one can tell whether it was hit."))
    itens = [L("Métrica", "Metric"), L("Linha de base", "Baseline"), L("Meta", "Target"), L("Prazo", "Deadline"),
             L("Fonte do dado", "Data source"), L("Dono", "Owner")]
    linhas = []
    for k_ in krs:
        linhas.append({"KR": k_["kr"], **{i: "✅" for i in itens}, L("Alavanca ligada", "Linked lever"): k_["alav"],
                       L("Dono", "Owner") + " ": k_["dono"]})
    linhas.append({"KR": ruins[0]["kr"], itens[0]: "❌", itens[1]: "❌", itens[2]: "❌", itens[3]: "❌", itens[4]: "❌", itens[5]: "❌",
                   L("Alavanca ligada", "Linked lever"): "–", L("Dono", "Owner") + " ": "–"})
    linhas.append({"KR": ruins[1]["kr"], itens[0]: "✅", itens[1]: "–", itens[2]: "✅", itens[3]: "✅", itens[4]: "❌", itens[5]: "❌",
                   L("Alavanca ligada", "Linked lever"): L("nova receita", "new revenue"), L("Dono", "Owner") + " ": "–"})
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")
    caixa(L("Sugestão pro KR de engajamento: <b>“% de assinantes que abriram 2 ou mais conteúdos no mês ≥ 45% em dez "
            "(linha de base set: 41%), fonte: eventos do app, dono: Head de Produto”</b>. Aí ele vira um KR que dá pra acompanhar.",
            "Suggestion for the engagement KR: <b>“% of subscribers who opened 2+ titles in the month ≥ 45% in Dec "
            "(Sep baseline: 41%), source: app events, owner: Head of Product”</b>. Then it becomes a KR you can track."))
    st.caption(L("Farol: verde com 70% ou mais de chance, amarelo entre 40% e 70%, vermelho abaixo de 40%.",
                 "Light: green at 70%+ chance, yellow between 40% and 70%, red below 40%."))

# ================================================================== PARCEIROS
with abas[5]:
    st.subheader(L("Quem dá dinheiro e quem só dá volume", "Who brings money and who only brings volume"))
    rent = M.rentabilidade(real, ULT)
    fig = go.Figure(go.Scatter(
        x=rent.base_media, y=rent.mc_pct, mode="markers+text", text=[V(p) for p in rent.index], textposition="top center",
        marker=dict(size=np.sqrt(rent.mc.clip(lower=1)) / 3.2, color=[VERMELHO if p == "Varejo Delta" else AZUL for p in rent.index],
                    opacity=0.75, line=dict(width=1, color="white")),
        customdata=np.stack([rent.mc, rent.ltv, rent.churn], axis=1),
        hovertemplate=L("%{text}<br>Base média: %{x:,.0f} mil<br>Margem: %{y:.1f}%<br>LTV: R$ %{customdata[1]:.0f}<br>Churn: %{customdata[2]:.1f}%/mês<extra></extra>",
                        "%{text}<br>Avg base: %{x:,.0f}K<br>Margin: %{y:.1f}%<br>LTV: R$ %{customdata[1]:.0f}<br>Churn: %{customdata[2]:.1f}%/mo<extra></extra>")))
    lay(fig, L("<b>Rentabilidade por parceiro</b> · últimos 12 meses · bolha = margem em R$", "<b>Profitability by partner</b> · last 12 months · bubble = margin in R$"), height=430)
    fig.update_xaxes(title=L("Base média (mil assinantes)", "Average base (K subscribers)"))
    fig.update_yaxes(title=L("Margem de contribuição (%)", "Contribution margin (%)"))
    st.plotly_chart(fig, width="stretch")
    tab = pd.DataFrame({
        L("Parceiro", "Partner"): [V(p) for p in rent.index],
        L("Receita", "Revenue"): [din(v) for v in rent.receita],
        L("Margem", "Margin"): [din(v) for v in rent.mc],
        L("Margem %", "Margin %"): [pct(v) for v in rent.mc_pct],
        L("Churn/mês", "Churn/mo"): [pct(v) for v in rent.churn],
        L("Margem por assinante/mês", "Margin per subscriber/mo"): [f"R$ {br(v, 2)}" for v in rent.mc_assinante_mes],
        "LTV": [f"R$ {br(v, 0)}" for v in rent.ltv],
    })
    st.dataframe(tab, hide_index=True, width="stretch")
    d_ = rent.loc["Varejo Delta"]
    como_ler(
        L("no gráfico, quanto mais à <b>direita</b>, mais assinantes o parceiro tem; quanto mais <b>alto</b>, maior a fatia da "
          "receita que vira margem; o <b>tamanho da bolha</b> é a margem em reais. O ideal é a bolha grande, alta e à direita. "
          "O <b>LTV</b> é quanto de margem um assinante deixa durante todo o tempo que fica: margem por mês ÷ churn.",
          "in the chart, the further <b>right</b>, the more subscribers the partner has; the <b>higher</b>, the bigger the share of "
          "revenue that becomes margin; <b>bubble size</b> is the margin in reais. The ideal is a big bubble, high and to the right. "
          "<b>LTV</b> is how much margin a subscriber leaves over their whole stay: monthly margin ÷ churn."),
        L(f"no Varejo Delta, cada assinante deixa R$ {br(d_.mc_assinante_mes, 2)} de margem por mês e {pct(d_.churn)} cancelam todo mês, "
          f"ou seja, o assinante fica em média uns {br(100 / d_.churn, 0)} meses. R$ {br(d_.mc_assinante_mes, 2)} × {br(100 / d_.churn, 0)} meses "
          f"= LTV de R$ {br(d_.ltv, 0)}.",
          f"at Delta Retail, each subscriber leaves R$ {br(d_.mc_assinante_mes, 2)} of margin per month and {pct(d_.churn)} cancel every month, "
          f"so a subscriber stays about {br(100 / d_.churn, 0)} months on average. R$ {br(d_.mc_assinante_mes, 2)} × {br(100 / d_.churn, 0)} months "
          f"= LTV of R$ {br(d_.ltv, 0)}."))
    caixa(L(f"O <b>Varejo Delta</b> é o pior da carteira: churn de {pct(d_.churn)} ao mês e LTV de R$ {br(d_.ltv)}, contra "
            f"R$ {br(rent.drop('Varejo Delta').ltv.median())} da mediana dos outros. Ele traz volume, mas cada assinante fica pouco e deixa pouca margem.",
            f"<b>Delta Retail</b> is the worst in the portfolio: {pct(d_.churn)} monthly churn and an LTV of R$ {br(d_.ltv)}, versus "
            f"R$ {br(rent.drop('Varejo Delta').ltv.median())} for the median of the others. It brings volume, but each subscriber stays briefly and leaves little margin."))
    st.markdown(L("#### Simulador de renegociação", "#### Renegotiation simulator"))
    s = st.columns(3)
    b2b = [p for p in rent.index if p != M.DIRETO]
    alvo_p = s[0].selectbox(L("Parceiro", "Partner"), b2b, index=b2b.index("Varejo Delta"), format_func=V)
    alvo_mc = s[1].slider(L("Margem % desejada", "Target margin %"), 30, 80, 60, 5)
    queda = s[2].slider(L("Churn depois da ação (%/mês)", "Churn after action (%/mo)"), 2.0, 12.0, float(round(rent.loc[alvo_p].churn, 1)), 0.5)
    pr_ = c_premissas(ULT).loc[alvo_p]
    tarifa_min = pr_.custo / (1 - alvo_mc / 100)
    ltv_novo = (pr_.preco - pr_.custo) / (queda / 100)
    ltv_mais = (max(tarifa_min, pr_.preco) - pr_.custo) / (queda / 100)
    k = st.columns(3)
    k[0].metric(L("Tarifa hoje", "Fee today"), f"R$ {br(pr_.preco, 2)}")
    k[1].metric(L(f"Tarifa mínima pra {alvo_mc}% de margem", f"Minimum fee for {alvo_mc}% margin"), f"R$ {br(tarifa_min, 2)}",
                pct((tarifa_min / pr_.preco - 1) * 100, 0, True))
    k[2].metric(L("LTV com o churn novo", "LTV with the new churn"), f"R$ {br(ltv_novo, 0)}",
                pct((ltv_novo / rent.loc[alvo_p].ltv - 1) * 100, 0, True))
    st.caption(L("Simulador: escolha o parceiro, a margem que a empresa quer ter com ele e quanto o churn cairia com uma ação de retenção. "
                 "Ele devolve a tarifa mínima pra pedir na renegociação e quanto o assinante passaria a valer.",
                 "Simulator: pick the partner, the margin the company wants with it and how much churn would drop with a retention action. "
                 "It returns the minimum fee to ask for in the renegotiation and how much a subscriber would be worth."))
    st.caption(L(f"Com a tarifa mínima e o churn novo juntos, o LTV vai a R$ {br(ltv_mais, 0)}. LTV aqui = margem por assinante por mês ÷ churn mensal.",
                 f"With the minimum fee and the new churn together, LTV goes to R$ {br(ltv_mais, 0)}. LTV here = margin per subscriber per month ÷ monthly churn."))

# ================================================================== NOVO PAÍS
with abas[6]:
    st.subheader(L("Vale abrir um país novo?", "Is a new country worth it?"))
    st.markdown(L("Business case de entrada num mercado novo pelo mesmo modelo B2B2C. **As premissas abaixo são ilustrativas**, "
                  "não são dados de mercado: a ideia é mostrar a estrutura da decisão. Mude e veja a resposta mudar.",
                  "Business case for entering a new market with the same B2B2C model. **The assumptions below are illustrative**, "
                  "not market data: the point is the structure of the decision. Change them and watch the answer change."))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(L("**Tamanho do mercado**", "**Market size**"))
        pop = st.number_input(L("População adulta (mil)", "Adult population (K)"), value=30000, step=1000)
        smart = st.slider(L("% com smartphone", "% with a smartphone"), 40, 95, 75)
        parc = st.slider(L("% que é cliente dos parceiros-alvo", "% who are customers of target partners"), 5, 60, 25)
        rampa = st.slider(L("Meses até todos os parceiros entrarem", "Months until all partners are live"), 1, 18, 6)
    with c2:
        st.markdown(L("**Assinantes e preço**", "**Subscribers and price**"))
        ativ_p = st.slider(L("Ativação ao mês (% da elegível)", "Monthly activation (% of eligible)"), 0.1, 1.5, 0.65, 0.05, format="%.2f%%")
        churn_p = st.slider(L("Churn ao mês (%)", "Monthly churn (%)"), 2.0, 15.0, 6.5, 0.5)
        tarifa_p = st.slider(L("Tarifa por assinante (R$/mês)", "Fee per subscriber (R$/mo)"), 1.0, 6.0, 2.90, 0.1)
        custo_p = st.slider(L("Custo de conteúdo (R$/assinante)", "Content cost (R$/subscriber)"), 0.5, 3.0, 1.30, 0.1)
    with c3:
        st.markdown(L("**Investimento**", "**Investment**"))
        inv = st.number_input(L("Investimento inicial (R$ mil)", "Upfront investment (R$ K)"), value=4500, step=500,
                              help=L("Catálogo local, tradução, integração com os parceiros, abertura de empresa.",
                                     "Local catalog, translation, partner integration, company setup."))
        fixo_p = st.number_input(L("Custo fixo local (R$ mil/mês)", "Local fixed cost (R$ K/mo)"), value=320, step=20)
        desc = st.slider(L("Taxa de desconto (% ao ano)", "Discount rate (%/yr)"), 5, 30, 15)
        faixa = st.slider(L("Incerteza das premissas (±%)", "Assumption uncertainty (±%)"), 5, 50, 25, 5,
                          help=L("Quanto ativação, churn e tarifa podem variar pra cima ou pra baixo nas simulações.",
                                 "How much activation, churn and fee can vary up or down in the simulations."))
    elegivel = pop * smart / 100 * parc / 100
    regime = elegivel * (ativ_p / 100) / (churn_p / 100)
    p_bc = dict(elegivel=elegivel, ativ=ativ_p / 100, churn=churn_p / 100, tarifa=tarifa_p, custo=custo_p, investimento=inv,
                fixo=fixo_p, rampa=rampa, desconto_aa=desc / 100, faixa_ativ=faixa / 100, faixa_churn=faixa / 200,
                faixa_tarifa=faixa / 250)
    (fluxo, vpl, payback), sims_bc = M.business_case(p_bc, 36, np.random.default_rng(11), n_sim=800)
    p_vpl = float((sims_bc.vpl > 0).mean())
    p_pb24 = float((sims_bc.payback <= 24).mean())

    f1, f2 = st.columns([1, 1.4])
    with f1:
        fig = go.Figure(go.Funnel(
            y=[L("População adulta", "Adult population"), L("Com smartphone", "With a smartphone"),
               L("Elegível (clientes dos parceiros)", "Eligible (partner customers)"), L("Base em regime", "Steady-state base")],
            x=[pop, pop * smart / 100, elegivel, regime], textinfo="value", texttemplate="%{value:,.0f}",
            marker=dict(color=[AZUL_CLARO, "#6ba3e6", AZUL, AZUL_ESC])))
        lay(fig, L("<b>Do mercado à base</b> · mil pessoas", "<b>From market to base</b> · K people"), height=360)
        st.plotly_chart(fig, width="stretch")
        st.caption(L("Base em regime = elegível × ativação ÷ churn (o ponto em que entra o mesmo tanto que sai).",
                     "Steady-state base = eligible × activation ÷ churn (where inflow equals outflow)."))
    with f2:
        fig = go.Figure()
        fig.add_scatter(x=fluxo.mes, y=fluxo.caixa, name=L("Caixa acumulado", "Cumulative cash"), fill="tozeroy",
                        line=dict(color=AZUL_ESC, width=2.5), fillcolor="rgba(42,120,214,0.12)")
        fig.add_hline(y=0, line=dict(color=CINZA, dash="dash"))
        if payback:
            fig.add_vline(x=payback, line=dict(color=VERDE, dash="dot"))
            fig.add_annotation(x=payback, y=0, text=L(f"se paga no mês {payback}", f"pays back in month {payback}"), showarrow=True, ay=-40)
        lay(fig, L("<b>Caixa acumulado em 36 meses</b> · R$ mil", "<b>Cumulative cash over 36 months</b> · R$ K"), height=360)
        fig.update_xaxes(title=L("Mês desde a entrada", "Month since entry"))
        st.plotly_chart(fig, width="stretch")

    como_ler(
        L("o <b>funil</b> mostra de onde saem os assinantes: da população, quem tem smartphone; desses, quem é cliente dos "
          "parceiros (a base elegível); e a <b>base em regime</b>, o tamanho em que a base para de crescer porque entra o mesmo "
          "tanto que sai. O <b>caixa acumulado</b> começa negativo (o investimento) e sobe conforme a base cresce; o mês em que "
          "ele cruza o zero é o <b>payback</b>. O <b>VPL</b> é todo o dinheiro dos 36 meses trazido pra valor de hoje, já "
          "descontado o investimento: positivo quer dizer que a aposta paga o custo do dinheiro.",
          "the <b>funnel</b> shows where subscribers come from: from the population, who has a smartphone; of those, who are partner "
          "customers (the eligible base); and the <b>steady-state base</b>, the size at which the base stops growing because inflow "
          "equals outflow. <b>Cumulative cash</b> starts negative (the investment) and rises as the base grows; the month it crosses "
          "zero is the <b>payback</b>. <b>NPV</b> is all the money over 36 months brought to today's value, net of the investment: "
          "positive means the bet pays for the cost of money."),
        L(f"com {gente(elegivel)} de elegíveis, {pct(ativ_p, 2)} ativando por mês e {pct(churn_p, 1)} cancelando, a base estaciona em "
          f"{gente(elegivel)} × {pct(ativ_p, 2)} ÷ {pct(churn_p, 1)} ≈ <b>{gente(regime)}</b> assinantes. Cada um deixa "
          f"R$ {br(tarifa_p - custo_p, 2)} por mês (tarifa − custo), o que dá uns {din(regime * (tarifa_p - custo_p))} por mês, "
          f"contra {din(fixo_p)} de custo fixo local.",
          f"with {gente(elegivel)} eligible, {pct(ativ_p, 2)} activating per month and {pct(churn_p, 1)} cancelling, the base settles at "
          f"{gente(elegivel)} × {pct(ativ_p, 2)} ÷ {pct(churn_p, 1)} ≈ <b>{gente(regime)}</b> subscribers. Each leaves R$ {br(tarifa_p - custo_p, 2)} "
          f"a month (fee − cost), about {din(regime * (tarifa_p - custo_p))} a month, against {din(fixo_p)} of local fixed cost."))
    k = st.columns(4)
    k[0].metric(L("VPL em 36 meses", "NPV over 36 months"), din(vpl))
    k[1].metric("Payback", L(f"mês {payback}", f"month {payback}") if payback else L("não se paga em 36 meses", "no payback in 36 months"))
    k[2].metric(L("Chance de VPL positivo", "Chance of positive NPV"), pct(p_vpl * 100, 0))
    k[3].metric(L("Chance de se pagar em até 24 meses", "Chance of payback within 24 months"), pct(p_pb24 * 100, 0))
    if p_vpl >= 0.7:
        dec, cor_d = L("Seguir", "Go"), "verde"
        txt = L("Mesmo com as premissas variando, a entrada se paga na maioria dos cenários.", "Even with the assumptions varying, entry pays off in most scenarios.")
    elif p_vpl >= 0.4:
        dec, cor_d = L("Seguir só com condição", "Go only with conditions"), "amarelo"
        txt = L("O resultado depende de premissas que ainda não estão confirmadas. Antes de investir, validar com um piloto "
                "a ativação real com 1 parceiro e fechar a tarifa em contrato.",
                "The result hinges on assumptions not yet confirmed. Before investing, validate real activation with a pilot "
                "with 1 partner and lock the fee in a contract.")
    else:
        dec, cor_d = L("Descartar por enquanto", "Drop for now"), "vermelho"
        txt = L("Na maioria dos cenários o investimento não volta. Os dados dizem pra descartar a aposta, ou rever o modelo de entrada.",
                "In most scenarios the investment doesn't come back. The data says drop this bet, or rethink the entry model.")
    fundo, cor_t, ic, _ = FAROL[cor_d]
    st.markdown(f"<div class='kr' style='background:{fundo};border-left:6px solid {cor_t};min-height:0'>"
                f"<div class='t'>{L('Recomendação', 'Recommendation')}</div><div class='b' style='color:{cor_t}'>{ic} {dec}</div>"
                f"<div class='m'>{txt}</div></div>", unsafe_allow_html=True)

    st.markdown(L("#### Onde está a fronteira", "#### Where the line is"))
    ativs = np.round(np.linspace(ativ_p * 0.6, ativ_p * 1.4, 7), 3)
    tarifas = np.round(np.linspace(tarifa_p * 0.7, tarifa_p * 1.3, 7), 2)
    z = np.zeros((len(tarifas), len(ativs)))
    for a_i, a_ in enumerate(ativs):
        for t_i, t_ in enumerate(tarifas):
            _, _, pb = M.business_case({**p_bc, "ativ": a_ / 100, "tarifa": t_}, 36)
            z[t_i, a_i] = pb if pb else np.nan
    fig = go.Figure(go.Heatmap(
        z=z, x=[pct(a, 2) for a in ativs], y=[f"R$ {br(t, 2)}" for t in tarifas],
        colorscale=[[0, "#1b7a3a"], [0.5, "#f5d27a"], [1, "#e34948"]], zmin=6, zmax=36,
        text=np.where(np.isnan(z), "—", np.vectorize(lambda v: f"{v:.0f}" if not np.isnan(v) else "—")(z)),
        texttemplate="%{text}", colorbar=dict(title=L("meses", "months")),
        hovertemplate=L("Ativação %{x} · tarifa %{y}<br>payback: %{text} meses<extra></extra>",
                        "Activation %{x} · fee %{y}<br>payback: %{text} months<extra></extra>")))
    lay(fig, L("<b>Payback (meses) por ativação × tarifa</b> · “—” = não se paga em 36 meses",
               "<b>Payback (months) by activation × fee</b> · “—” = no payback within 36 months"), height=380)
    fig.update_xaxes(title=L("Ativação ao mês", "Monthly activation"), showgrid=False)
    fig.update_yaxes(title=L("Tarifa", "Fee"), showgrid=False)
    st.plotly_chart(fig, width="stretch")
    como_ler(
        L("cada quadrado é uma combinação de ativação (coluna) e tarifa (linha), e o número é em quantos meses o país se paga. "
          "Verde = se paga rápido, vermelho = demora, “—” = não se paga em 3 anos. A fronteira entre as cores mostra o mínimo "
          "que precisa ser verdade pra aposta valer, e é isso que um piloto deve testar antes do investimento grande.",
          "each square is a combination of activation (column) and fee (row), and the number is how many months until the country "
          "pays back. Green = fast, red = slow, “—” = no payback within 3 years. The border between colors shows the minimum that "
          "must be true for the bet to work, and that's what a pilot should test before the big investment."))

# ================================================================== COMO FUNCIONA
with abas[7]:
    st.subheader(L("Como o Janus faz as contas", "How Janus does the math"))
    st.markdown(L("""
**1. Uma conta só.** Todo o app roda a mesma árvore (aba *O case*), mês a mês e por parceiro. O que muda entre plano,
realizado, forecast e simulação são só as premissas que entram nela. Por isso os números conversam entre as abas.

**2. Premissas recentes.** O ponto de partida do forecast é a média dos últimos 12 meses de cada alavanca, com peso
maior pros meses recentes (o peso cai pela metade a cada 3 meses). Assim, se algo mudou em abril, o forecast já
enxerga a mudança sem esquecer o histórico.

**3. Sazonalidade.** A ativação tem meses mais fortes (janeiro, novembro) e mais fracos (junho). O fator de cada mês
foi estimado em 2024–2025: a taxa do mês dividida pela média do ano daquele parceiro.

**4. Incerteza (Monte Carlo).** Em cada uma das 600 simulações, ativação, churn e CAC de cada parceiro ganham um
desvio do tamanho da variação que eles já tiveram no histórico, mais uma deriva que cresce com o tempo. A faixa
P10–P90 é onde caem 80% das simulações. É daí que saem a chance de bater o plano e a chance de cada KR.

**5. Ponte de variação.** Pra explicar a diferença entre plano e realizado, a conta é refeita trocando uma alavanca
por vez (elegíveis → ativação → verba → CAC → churn → preço → custo). Quanto a margem mudou em cada troca é o efeito
daquela alavanca. A ordem importa um pouco; por isso ela é fixa.

**6. Business case.** Fluxo de caixa mensal da entrada no país novo, com rampa dos parceiros, VPL descontado e 800
simulações das premissas dentro da faixa de incerteza escolhida.

---
**Exemplo da conta (passo 1):** um parceiro começa o mês com 500 mil assinantes, tem 6 milhões de elegíveis e taxa de
ativação de 0,7%. Entram 6.000.000 × 0,7% = 42 mil. Com churn de 7%, saem 500 mil × 7% = 35 mil. Termina o mês com
500 + 42 − 35 = **507 mil**. Com tarifa de R$ 2,90 e custo de R$ 1,05, a margem do mês é 507 mil × (2,90 − 1,05) ≈ **R$ 938 mil**.

**Exemplo do peso (passo 2):** o mês mais recente vale 1; o de 3 meses atrás vale ½; o de 6 meses atrás, ¼. Se a
ativação foi 0,8% por muito tempo e caiu pra 0,6% nos últimos 3 meses, a premissa fica mais perto de 0,6% do que de 0,8%.

**Exemplo da ponte (passo 5):** o plano previa R$ 100 de margem. Trocando só a ativação pela real, a conta dá R$ 97:
a ativação "custou" R$ 3. Trocando também o churn, dá R$ 98: o churn "devolveu" R$ 1. E assim por diante até trocar
tudo e chegar no realizado.
""", """
**1. One single calculation.** The whole app runs the same tree (see *The case*), month by month and per partner. Plan,
actuals, forecast and simulation only change the assumptions going in. That's why numbers match across tabs.

**2. Recent assumptions.** The forecast starts from the last 12 months of each lever, weighting recent months more
(the weight halves every 3 months). If something changed in April, the forecast already sees it without forgetting history.

**3. Seasonality.** Activation has stronger months (January, November) and weaker ones (June). Each month's factor was
estimated on 2024–2025: the month's rate divided by that partner's yearly average.

**4. Uncertainty (Monte Carlo).** In each of 600 simulations, each partner's activation, churn and CAC get a deviation
the size of their historical variation, plus a drift that grows over time. The P10–P90 band is where 80% of simulations
fall. That's where the chance of hitting the plan and each KR comes from.

**5. Variance bridge.** To explain the gap between plan and actuals, the calculation is redone swapping one lever at a
time (eligible → activation → budget → CAC → churn → price → cost). How much the margin moved at each swap is that
lever's effect. The order matters a little, so it is fixed.

**6. Business case.** Monthly cash flow for the new-country entry, with partner ramp-up, discounted NPV and 800
simulations of the assumptions within the chosen uncertainty range.

---
**Example of the math (step 1):** a partner starts the month with 500K subscribers, has 6 million eligible and a 0.7%
activation rate. In come 6,000,000 × 0.7% = 42K. With 7% churn, out go 500K × 7% = 35K. It ends the month with
500 + 42 − 35 = **507K**. With a R$ 2.90 fee and R$ 1.05 cost, the month's margin is 507K × (2.90 − 1.05) ≈ **R$ 938K**.

**Example of the weighting (step 2):** the latest month weighs 1; 3 months ago weighs ½; 6 months ago, ¼. If activation
was 0.8% for a long time and dropped to 0.6% in the last 3 months, the assumption lands closer to 0.6% than to 0.8%.

**Example of the bridge (step 5):** the plan expected R$ 100 of margin. Swapping only activation for the actual, the math
gives R$ 97: activation "cost" R$ 3. Swapping churn too, it gives R$ 98: churn "gave back" R$ 1. And so on until everything
is swapped and you reach the actual.
"""))
    st.markdown(L("#### O forecast acerta?", "#### Does the forecast work?"))
    bt = c_backtest()
    fig = go.Figure()
    fig.add_bar(x=bt.alvo, y=bt.erro_mc, name=L("Margem de contribuição", "Contribution margin"), marker_color=AZUL)
    fig.add_bar(x=bt.alvo, y=bt.erro_base, name=L("Base ativa", "Active base"), marker_color=AZUL_CLARO)
    lay(fig, L("<b>Erro do forecast 3 meses à frente</b> · % (previsto ÷ realizado − 1), mês a mês no passado",
               "<b>3-month-ahead forecast error</b> · % (forecast ÷ actual − 1), month by month in the past"), barmode="group", height=340)
    fig.update_yaxes(title="%")
    st.plotly_chart(fig, width="stretch")
    caixa(L(f"Em cada mês do passado, o Janus montou as premissas só com o que se sabia até ali e projetou 3 meses. "
            f"Erro médio (em módulo): <b>{br(bt.erro_mc.abs().mean(), 1)}%</b> na margem e <b>{br(bt.erro_base.abs().mean(), 1)}%</b> na base. "
            f"O erro cresce quando algo muda de repente (como a queda de ativação da Aurora em abril/2026): é pra isso que existem a faixa de incerteza e a leitura mensal.",
            f"For each past month, Janus built the assumptions using only what was known then and projected 3 months. "
            f"Mean absolute error: <b>{br(bt.erro_mc.abs().mean(), 1)}%</b> on margin and <b>{br(bt.erro_base.abs().mean(), 1)}%</b> on the base. "
            f"Error grows when something changes suddenly (like Aurora's activation drop in April 2026): that's what the uncertainty band and the monthly review are for."))
    with st.expander(L("O que foi plantado na base sintética (pra conferir a leitura do mês)", "What was planted in the synthetic data (to check the monthly review)")):
        st.markdown(L("""
- **Operadora Aurora**: ativação cai 28% a partir de abril/2026 (o parceiro escondeu o app num menu novo).
- **Varejo Delta**: churn piora 2,5% a cada mês de 2026.
- **Fintech Éter**: ativação 25% acima do histórico em 2026 (parceiro novo indo melhor que o plano).
- **Operadora Boreal**: reajuste de 8% na tarifa a partir de julho/2026, que o plano não tinha.
- **Canal direto**: CAC sobe 3% a cada mês de 2026 (leilão de mídia mais caro).
- O plano de 2026 foi montado em dez/2025 com a média de jun–nov/2025 e 3% de ambição na ativação.
""", """
- **Aurora Telecom**: activation drops 28% from April 2026 (the partner hid the app in a new menu).
- **Delta Retail**: churn worsens 2.5% every month of 2026.
- **Éter Fintech**: activation 25% above history in 2026 (new partner doing better than plan).
- **Boreal Telecom**: 8% fee increase from July 2026, not in the plan.
- **Direct channel**: CAC rises 3% every month of 2026 (pricier media auctions).
- The 2026 plan was built in Dec 2025 from the Jun–Nov 2025 average plus 3% activation ambition.
"""))
    saz_df = pd.DataFrame({"m": [mes_txt(pd.Timestamp(2025, m, 1)).split("/")[0] for m in range(1, 13)], "f": SAZ.values})
    fig = go.Figure(go.Bar(x=saz_df.m, y=saz_df.f, marker_color=[AZUL_ESC if v >= 1 else AZUL_CLARO for v in saz_df.f],
                           text=[br(v, 2) for v in saz_df.f], textposition="outside"))
    fig.add_hline(y=1, line=dict(color=CINZA, dash="dash"))
    lay(fig, L("<b>Fator sazonal da ativação</b> · 1 = mês médio", "<b>Activation seasonal factor</b> · 1 = average month"), height=300)
    fig.update_yaxes(range=[0.7, 1.3])
    st.plotly_chart(fig, width="stretch")

# ================================================================== GLOSSÁRIO
with abas[8]:
    st.subheader(L("Glossário", "Glossary"))
    termos = [
        ("B2B2C", "A empresa vende pra outra empresa (o parceiro), que entrega o produto pro cliente final. Aqui: a operadora paga uma tarifa por assinante e oferece o app pros clientes dela.",
         "The company sells to another company (the partner), which delivers the product to the end customer. Here: the telco pays a fee per subscriber and offers the app to its customers."),
        (L("Base elegível", "Eligible base"), "Clientes do parceiro que podem ativar o app.", "Partner customers who can activate the app."),
        (L("Taxa de ativação", "Activation rate"), "% da base elegível que ativa o app no mês.", "% of the eligible base that activates the app in the month."),
        ("Churn", "% da base que cancela no mês.", "% of the base that cancels in the month."),
        ("CAC", "Custo de aquisição: quanto de verba de marketing custa trazer um assinante no canal direto.", "Acquisition cost: how much marketing budget it takes to bring one subscriber in the direct channel."),
        (L("Margem de contribuição (MC)", "Contribution margin"), "Receita menos os custos que variam com o volume (conteúdo e marketing). Mostra quanto cada parceiro deixa pra pagar o custo fixo.",
         "Revenue minus the costs that vary with volume (content and marketing). Shows how much each partner leaves to pay fixed costs."),
        (L("Resultado operacional", "Operating result"), "Margem de contribuição menos o custo fixo (plataforma, time, catálogo).", "Contribution margin minus fixed cost (platform, team, catalog)."),
        ("LTV", "Quanto de margem um assinante deixa na vida média dele: margem por mês ÷ churn mensal.", "How much margin a subscriber leaves over their average lifetime: monthly margin ÷ monthly churn."),
        ("Forecast", "Projeção do futuro a partir do que está acontecendo agora. Diferente do plano, que é a meta combinada.", "Projection of the future from what is happening now. Different from the plan, which is the agreed target."),
        (L("Aterrissagem", "Landing"), "Realizado do ano até agora + forecast dos meses que faltam: onde o ano deve fechar.", "Year-to-date actuals + forecast for the remaining months: where the year should close."),
        (L("Ponte de variação", "Variance bridge"), "Gráfico que quebra a diferença entre plano e realizado em pedaços, um por alavanca.", "Chart that breaks the plan-vs-actual gap into pieces, one per lever."),
        (L("Cenário", "Scenario"), "Um conjunto de premissas (otimista, base, pessimista) pra ver o que acontece se o mundo for por um caminho ou outro.", "A set of assumptions (optimistic, base, pessimistic) to see what happens if the world goes one way or another."),
        (L("Sensibilidade (tornado)", "Sensitivity (tornado)"), "Mexe uma alavanca por vez e mede o efeito no resultado. A barra maior é a alavanca que mais importa.", "Moves one lever at a time and measures the effect on the result. The longest bar is the lever that matters most."),
        ("Monte Carlo", "Rodar a mesma conta centenas de vezes sorteando as premissas dentro do que é plausível, pra ver a faixa de resultados possíveis.", "Running the same calculation hundreds of times drawing the assumptions within what's plausible, to see the range of possible outcomes."),
        ("P10–P90", "Faixa onde caem 80% das simulações: 10% ficam abaixo, 10% acima.", "Range where 80% of simulations fall: 10% below, 10% above."),
        ("Backtest", "Testar o forecast no passado: fingir que estava num mês antigo, projetar e comparar com o que aconteceu.", "Testing the forecast on the past: pretend you're in an old month, project, and compare with what happened."),
        ("OKR", "Objetivo (aonde quer chegar) + Key Results (números que mostram se chegou).", "Objective (where you want to go) + Key Results (numbers that show whether you got there)."),
        ("KR", "Resultado-chave. Precisa de métrica, linha de base, meta, prazo, fonte e dono pra dar pra acompanhar.", "Key result. Needs a metric, baseline, target, deadline, source and owner to be trackable."),
        (L("Linha de base", "Baseline"), "Onde a métrica estava quando a meta foi definida.", "Where the metric stood when the target was set."),
        ("TAM / SAM", "Mercado total e a parte dele que dá pra alcançar com o modelo de negócio (aqui: clientes dos parceiros com smartphone).", "Total market and the part of it reachable with the business model (here: partner customers with a smartphone)."),
        (L("Base em regime", "Steady-state base"), "Tamanho em que a base para de crescer porque entra o mesmo tanto que sai: elegível × ativação ÷ churn.", "Size at which the base stops growing because inflow equals outflow: eligible × activation ÷ churn."),
        (L("VPL", "NPV"), "Valor presente líquido: soma do caixa futuro trazido pra hoje com uma taxa de desconto, menos o investimento.", "Net present value: future cash brought to today with a discount rate, minus the investment."),
        ("Payback", "Mês em que o caixa acumulado volta a ficar positivo.", "Month when cumulative cash turns positive again."),
        (L("Sazonalidade", "Seasonality"), "Padrão que se repete no mesmo mês todo ano.", "A pattern that repeats in the same month every year."),
    ]
    for t_, pt_, en_ in termos:
        st.markdown(f"**{t_}** · {L(pt_, en_)}")
