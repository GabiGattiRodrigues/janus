"""
Motor do Janus: a mesma conta serve pro plano, pro realizado, pro forecast e pras simulações.

A conta, mês a mês e por parceiro (valores em milhares):
    ativações      = elegível × taxa de ativação          (parceiros B2B2C)
                   = verba de marketing ÷ CAC              (canal direto)
    cancelamentos  = base do mês anterior × churn
    base           = base do mês anterior + ativações − cancelamentos
    receita        = base × preço (tarifa do parceiro ou preço líquido do app)
    custo          = base × custo de conteúdo por assinante
    margem (MC)    = receita − custo − verba de marketing
    resultado      = MC − custo fixo

Plano, realizado e forecast só mudam as premissas que entram nessa conta.
"""

import os

import numpy as np
import pandas as pd

PASTA_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")
DIRETO = "Direto (app)"
ALAVANCAS = ["elegivel", "ativ", "verba", "cac", "churn", "preco", "custo"]
MEIA_VIDA = 3          # meses: peso das premissas recentes cai pela metade a cada 3 meses
JANELA_TEND = 8        # meses usados pra ver se a alavanca vem subindo ou caindo
T_MIN = 3.0            # só aceita a tendência se ela for bem clara (estatística t da inclinação ≥ 3)
AMORTECE = 0.8         # a tendência perde 20% de força a cada mês do forecast


def tendencia(x):
    """
    Inclinação (em % ao mês) dos últimos JANELA_TEND meses, numa reta sobre o log da série.
    Devolve (inclinação, nível no último mês). Se a tendência não for clara (|t| < T_MIN),
    devolve (0, None) e a premissa fica com a média ponderada.
    """
    # Pegando só os últimos meses: o que interessa é se a alavanca está andando agora.
    x = np.asarray(x, dtype=float)[-JANELA_TEND:]
    if len(x) < JANELA_TEND or np.any(x <= 0):
        return 0.0, None
    # Reta no log: a inclinação vira % ao mês (0,03 ≈ +3% ao mês).
    y, t = np.log(x), np.arange(len(x))
    b, a = np.polyfit(t, y, 1)
    resid = y - (a + b * t)
    # Erro padrão da inclinação. Se a inclinação não for pelo menos T_MIN vezes esse erro, é ruído e não tendência.
    se = np.sqrt((resid ** 2).sum() / (len(x) - 2) / ((t - t.mean()) ** 2).sum())
    if se == 0 or abs(b / se) < T_MIN:
        return 0.0, None
    return float(b), float(np.exp(a + b * t[-1]))


def fator_tendencia(inclinacao, passos):
    """Efeito acumulado da tendência amortecida depois de `passos` meses."""
    # Soma de 0,8 + 0,8² + ... : no mês 1 a tendência anda 0,8 passo, no 2 anda mais 0,64 e assim vai.
    # No limite ela anda no máximo 4 passos, então nunca projeta subida infinita.
    soma = AMORTECE * (1 - AMORTECE ** passos) / (1 - AMORTECE)
    return np.exp(inclinacao * soma)


# ------------------------------------------------------------------ dados
def carregar():
    # Lendo o realizado (uma linha por parceiro e mês) e as premissas do plano 2026.
    # Margem de contribuição = receita - custo de conteúdo - verba de marketing.
    real = pd.read_csv(os.path.join(PASTA_DADOS, "realizado_mensal.csv"), parse_dates=["mes"])
    plano = pd.read_csv(os.path.join(PASTA_DADOS, "plano_2026.csv")).set_index("parceiro")
    real["mc_mil"] = real.receita_mil - real.custo_conteudo_mil - real.verba_mkt_mil
    return real, plano


def ordem_parceiros(real):
    """Parceiros na ordem de tamanho da base, direto por último."""
    # Ordenando pelo tamanho da base no último mês, pra tabela e gráfico seguirem sempre a mesma ordem.
    ult = real[real.mes == real.mes.max()].sort_values("base_final_mil", ascending=False)
    nomes = [p for p in ult.parceiro if p != DIRETO]
    return nomes + [DIRETO]


def fatores_sazonais(real):
    """
    Quanto cada mês do ano ativa acima/abaixo da média, estimado em 2024–2025.
    Taxa do mês ÷ média do ano daquele parceiro, depois média entre parceiros.
    """
    h = real[(real.mes.dt.year <= 2025)].copy()
    # Parceiro: taxa = ativações ÷ elegíveis. Direto: não tem elegível, então uso as ativações.
    h["taxa"] = np.where(h.parceiro == DIRETO, h.ativacoes_mil, h.ativacoes_mil / h.elegivel_mil)
    h["ano"] = h.mes.dt.year
    # Comparando cada mês com a média do ano daquele parceiro (1,10 = 10% acima da média).
    h["rel"] = h.taxa / h.groupby(["parceiro", "ano"]).taxa.transform("mean")
    # parceiro em rampa distorce o fator: só anos completos
    completos = h.groupby(["parceiro", "ano"]).mes.transform("count") == 12
    # Tirando a média por mês do ano entre parceiros e normalizando pra média dos 12 meses dar 1.
    f = h[completos].groupby(h.mes.dt.month).rel.mean()
    return (f / f.mean()).reindex(range(1, 13)).fillna(1.0)


# ------------------------------------------------------------------ a conta
def rodar(base0, tipo_direto, d):
    """
    Roda a conta para N parceiros × T meses.
    d: dict com arrays (N, T) para cada alavanca; base0: array (N,) com a base de partida.
    Devolve dict de arrays (N, T).
    """
    # Tudo vem em matriz (parceiros × meses), então a conta roda pra todos os parceiros de uma vez.
    n, t = d["churn"].shape
    base = np.zeros((n, t))
    # Ativações: no direto é verba ÷ CAC; nos parceiros é elegíveis × taxa de ativação.
    ativ = np.where(tipo_direto[:, None], d["verba"] / d["cac"], d["elegivel"] * d["ativ"])
    canc = np.zeros((n, t))
    anterior = base0.astype(float)
    # Andando mês a mês, porque a base de um mês depende da do mês anterior.
    for j in range(t):
        canc[:, j] = anterior * d["churn"][:, j]
        base[:, j] = anterior + ativ[:, j] - canc[:, j]
        anterior = base[:, j]
    # Receita e custo de conteúdo são por assinante ativo no fim do mês.
    receita = base * d["preco"]
    custo = base * d["custo"]
    # Verba de marketing só existe no canal direto (nos parceiros quem faz a aquisição é o parceiro).
    verba = np.where(tipo_direto[:, None], d["verba"], 0.0)
    return dict(base=base, ativacoes=ativ, cancelamentos=canc, receita=receita,
                custo=custo, verba=verba, mc=receita - custo - verba)


def drivers_realizados(real, parceiros, meses):
    """As alavancas que de fato aconteceram, lidas da base (inverso da conta)."""
    d = {k: np.zeros((len(parceiros), len(meses))) for k in ALAVANCAS}
    r = real.set_index(["parceiro", "mes"])
    for i, p in enumerate(parceiros):
        for j, m in enumerate(meses):
            # Parceiro ainda não existia nesse mês: deixando zerado.
            if (p, m) not in r.index:
                d["churn"][i, j] = 0.0
                d["cac"][i, j] = 1.0
                continue
            x = r.loc[(p, m)]
            d["elegivel"][i, j] = x.elegivel_mil
            # Fazendo a conta ao contrário: a partir do que aconteceu, descobrindo qual foi cada alavanca no mês.
            d["ativ"][i, j] = x.ativacoes_mil / x.elegivel_mil if x.elegivel_mil > 0 else 0.0
            d["verba"][i, j] = x.verba_mkt_mil
            d["cac"][i, j] = x.verba_mkt_mil / x.ativacoes_mil if p == DIRETO else 1.0
            # Churn = cancelamentos ÷ base do início do mês.
            d["churn"][i, j] = x.cancelamentos_mil / x.base_inicial_mil if x.base_inicial_mil > 0 else 0.0
            d["preco"][i, j] = x.preco_unit
            d["custo"][i, j] = x.custo_conteudo_mil / x.base_final_mil if x.base_final_mil > 0 else 0.0
    return d


def drivers_plano(plano, parceiros, meses, sazonal):
    """As alavancas do plano 2026: premissas fixas, ativação com sazonalidade."""
    d = {k: np.zeros((len(parceiros), len(meses))) for k in ALAVANCAS}
    for i, p in enumerate(parceiros):
        x = plano.loc[p]
        for j, m in enumerate(meses):
            s = sazonal[m.month]
            passo = j + 1
            # Plano: elegíveis crescendo no ritmo combinado com o parceiro, a partir de dez/2025.
            d["elegivel"][i, j] = x.elegivel_dez25_mil * (1 + x.cresc_elegivel_mes) ** passo
            # A ativação do plano segue a sazonalidade (janeiro e novembro mais fortes).
            d["ativ"][i, j] = 0.0 if np.isnan(x.ativacao_mes) else x.ativacao_mes * s
            d["verba"][i, j] = x.verba_mkt_mes_mil * s if p == DIRETO else 0.0
            d["cac"][i, j] = x.cac if p == DIRETO else 1.0
            d["churn"][i, j] = x.churn_mes
            d["preco"][i, j] = x.preco_unit
            d["custo"][i, j] = x.custo_unit
    return d


def base_inicial(real, parceiros, mes_anterior):
    r = real[real.mes == mes_anterior].set_index("parceiro")
    return np.array([r.base_final_mil.get(p, 0.0) for p in parceiros])


# ------------------------------------------------------------------ plano x realizado
def plano_mensal_2026(real, plano, parceiros, sazonal):
    meses = pd.date_range("2026-01-01", "2026-12-01", freq="MS")
    tipo = np.array([p == DIRETO for p in parceiros])
    base0 = plano.loc[parceiros].base_dez25_mil.to_numpy()
    out = rodar(base0, tipo, drivers_plano(plano, parceiros, meses, sazonal))
    return meses, out


def ponte(real, plano, parceiros, sazonal, ate):
    """
    Ponte de variação da margem de contribuição (MC) acumulada de jan/2026 até `ate`:
    troca as premissas do plano pelas realizadas uma alavanca por vez, sempre na mesma
    ordem, e mede quanto a MC mudou a cada troca. A soma das peças fecha exatamente
    a diferença entre realizado e plano.
    """
    meses = pd.date_range("2026-01-01", ate, freq="MS")
    tipo = np.array([p == DIRETO for p in parceiros])
    base0 = plano.loc[parceiros].base_dez25_mil.to_numpy()
    dp = drivers_plano(plano, parceiros, meses, sazonal)
    dr = drivers_realizados(real, parceiros, meses)
    # Começando com todas as alavancas do plano.
    atual = {k: v.copy() for k, v in dp.items()}
    mc_ant = rodar(base0, tipo, atual)["mc"].sum(axis=1)
    pecas = []
    grupos = [("elegivel", ["elegivel"]), ("ativ", ["ativ"]), ("verba", ["verba"]), ("cac", ["cac"]),
              ("churn", ["churn"]), ("preco", ["preco"]), ("custo", ["custo"])]
    # Trocando uma alavanca por vez pelo realizado e medindo quanto a margem andou em cada troca.
    # Como cada troca parte da anterior, as peças somam exatamente realizado - plano.
    for nome, chaves in grupos:
        for k in chaves:
            atual[k] = dr[k]
        mc = rodar(base0, tipo, atual)["mc"].sum(axis=1)
        for i, p in enumerate(parceiros):
            pecas.append(dict(alavanca=nome, parceiro=p, efeito_mil=mc[i] - mc_ant[i]))
        mc_ant = mc
    pecas = pd.DataFrame(pecas)
    mc_plano = rodar(base0, tipo, dp)["mc"].sum()
    mc_real = rodar(base0, tipo, dr)["mc"].sum()       # igual ao realizado, sem o arredondamento da base
    return pecas, mc_plano, mc_real


# ------------------------------------------------------------------ premissas recentes
def premissas_recentes(real, parceiros, ate, sazonal, janela=12):
    """
    Premissa de cada alavanca = média dos últimos meses com peso maior pros mais recentes
    (meia-vida de 3 meses), tirando a sazonalidade da ativação. Ativação, churn e CAC que vêm
    subindo ou caindo de forma clara nos últimos 8 meses ganham tendência (amortecida no forecast).
    Também guarda a variação mês a mês de cada taxa, que vira a incerteza do forecast.
    """
    meses = pd.date_range(pd.Timestamp(ate) - pd.DateOffset(months=janela - 1), ate, freq="MS")
    d = drivers_realizados(real, parceiros, meses)
    # Peso de cada mês: o mais recente vale 1, o de 3 meses atrás vale 0,5, o de 6 meses atrás 0,25.
    peso = 0.5 ** (np.arange(len(meses))[::-1] / MEIA_VIDA)
    s = np.array([sazonal[m.month] for m in meses])
    linhas = []
    for i, p in enumerate(parceiros):
        # Ignorando meses em que o parceiro ainda não existia (a Éter entrou em mar/2025).
        valido = d["churn"][i] > 0
        w = peso * valido
        if w.sum() == 0:
            continue
        def media(x):
            return float((x * w).sum() / w.sum())
        def cv(x):
            x = x[valido]
            return float(np.std(x) / np.mean(x)) if len(x) > 2 and np.mean(x) > 0 else 0.0
        # Tirando a sazonalidade antes de tirar a média; ela volta mês a mês no forecast.
        ativ_des = d["ativ"][i] / s
        verba_des = d["verba"][i] / s
        cresc = (d["elegivel"][i, -1] / d["elegivel"][i, valido][0]) ** (1 / max(1, valido.sum() - 1)) - 1 \
            if p != DIRETO else 0.0
        # tendência: se a alavanca vem andando de forma clara, o nível parte do último mês da reta
        # (não da média, que fica pra trás) e o forecast segue a inclinação, amortecida
        # Verificando se ativação, churn e CAC vêm subindo ou caindo de forma clara.
        t_ativ, n_ativ = tendencia(ativ_des[valido]) if p != DIRETO else (0.0, None)
        t_churn, n_churn = tendencia(d["churn"][i][valido])
        t_cac, n_cac = tendencia(d["cac"][i][valido]) if p == DIRETO else (0.0, None)
        linhas.append(dict(
            parceiro=p, direto=p == DIRETO,
            elegivel=d["elegivel"][i, -1], cresc=cresc,
            ativ=(n_ativ or media(ativ_des)) if p != DIRETO else 0.0,
            verba=media(verba_des) if p == DIRETO else 0.0,
            cac=(n_cac or media(d["cac"][i])) if p == DIRETO else 1.0,
            churn=n_churn or media(d["churn"][i]), preco=d["preco"][i, -1], custo=media(d["custo"][i]),
            tend_ativ=t_ativ, tend_churn=t_churn, tend_cac=t_cac,
            # Quanto cada taxa costuma variar de um mês pro outro (desvio ÷ média). É isso que alimenta a incerteza das simulações.
            cv_ativ=cv(ativ_des) if p != DIRETO else 0.0,
            cv_cac=cv(d["cac"][i]) if p == DIRETO else 0.0,
            cv_churn=cv(d["churn"][i]),
        ))
    return pd.DataFrame(linhas).set_index("parceiro")


# ------------------------------------------------------------------ forecast
CENARIOS = {
    # multiplicadores sobre as premissas recentes; reajuste = % ao ano no preço
    "base": dict(ativ=1.00, churn=1.00, cac=1.00, custo=1.00, verba=1.00, reajuste=0.00, cresc=1.0),
    # Otimista: +10% ativação, -8% churn, -5% CAC e reajuste de 4% ao ano.
    "otimista": dict(ativ=1.10, churn=0.92, cac=0.95, custo=0.98, verba=1.00, reajuste=0.04, cresc=1.3),
    # Pessimista: -12% ativação, +10% churn, +12% CAC e sem reajuste.
    "pessimista": dict(ativ=0.88, churn=1.10, cac=1.12, custo=1.04, verba=1.00, reajuste=0.00, cresc=0.6),
}


def drivers_futuros(prem, meses, sazonal, mult=None, mult_parceiro=None):
    """Alavancas dos meses futuros a partir das premissas recentes (e dos ajustes de cenário)."""
    mult = mult or CENARIOS["base"]
    mult_parceiro = mult_parceiro or {}
    n, t = len(prem), len(meses)
    d = {k: np.zeros((n, t)) for k in ALAVANCAS}
    for i, (p, x) in enumerate(prem.iterrows()):
        mp = mult_parceiro.get(p, {})
        for j, m in enumerate(meses):
            s = sazonal[m.month]
            anos = (j + 1) / 12
            # Montando cada alavanca do mês futuro: premissa recente × tendência × sazonalidade × ajuste do cenário.
            d["elegivel"][i, j] = x.elegivel * (1 + x.cresc * mult.get("cresc", 1.0)) ** (j + 1)
            d["ativ"][i, j] = x.ativ * fator_tendencia(x.tend_ativ, j + 1) * s * mult["ativ"] * mp.get("ativ", 1.0)
            d["verba"][i, j] = x.verba * s * mult["verba"] * mp.get("verba", 1.0)
            d["cac"][i, j] = x.cac * fator_tendencia(x.tend_cac, j + 1) * mult["cac"] * mp.get("cac", 1.0)
            d["churn"][i, j] = min(0.5, x.churn * fator_tendencia(x.tend_churn, j + 1) * mult["churn"] * mp.get("churn", 1.0))
            # reajuste anual de preço a cada janeiro
            # Reajuste de preço entra todo janeiro.
            reaj = (1 + mult["reajuste"]) ** sum(1 for mm in meses[:j + 1] if mm.month == 1)
            d["preco"][i, j] = x.preco * reaj * mp.get("preco", 1.0)
            d["custo"][i, j] = x.custo * mult["custo"] * mp.get("custo", 1.0) * (1 + 0.5 * mult["reajuste"]) ** int(anos)   # custo acompanha metade do reajuste
    return d


def forecast(real, prem, ate, meses_a_frente, sazonal, mult=None, mult_parceiro=None):
    meses = pd.date_range(pd.Timestamp(ate) + pd.DateOffset(months=1), periods=meses_a_frente, freq="MS")
    parceiros = list(prem.index)
    tipo = prem.direto.to_numpy()
    base0 = base_inicial(real, parceiros, pd.Timestamp(ate))
    return meses, rodar(base0, tipo, drivers_futuros(prem, meses, sazonal, mult, mult_parceiro))


def simular(real, prem, ate, meses_a_frente, sazonal, n_sim=600, semente=7, mult=None, deriva=0.012):
    """
    Monte Carlo do forecast. Em cada simulação, a ativação, o churn e o CAC de cada parceiro
    ganham (1) um desvio que dura o horizonte inteiro, do tamanho da variação histórica, e
    (2) uma deriva que cresce com o tempo (quanto mais longe, mais incerto).
    Devolve arrays (n_sim, N, T).
    """
    rng = np.random.default_rng(semente)
    meses = pd.date_range(pd.Timestamp(ate) + pd.DateOffset(months=1), periods=meses_a_frente, freq="MS")
    parceiros = list(prem.index)
    tipo = prem.direto.to_numpy()
    base0 = base_inicial(real, parceiros, pd.Timestamp(ate))
    d0 = drivers_futuros(prem, meses, sazonal, mult)
    n, t = len(parceiros), len(meses)
    res = {k: np.zeros((n_sim, n, t)) for k in ["base", "ativacoes", "cancelamentos", "receita", "custo", "verba", "mc"]}
    cac_sim = np.zeros((n_sim, n, t))
    for s in range(n_sim):
        d = {k: v.copy() for k, v in d0.items()}
        for chave, cvcol in [("ativ", "cv_ativ"), ("churn", "cv_churn"), ("cac", "cv_cac")]:
            # Piso de 3% de variação, pra nenhuma alavanca ficar sem incerteza nenhuma.
            cv = np.maximum(prem[cvcol].to_numpy(), 0.03)[:, None]
            # Desvio que vale pro horizonte todo (ex.: nessa simulação o churn da Delta fica 4% mais alto).
            nivel = rng.normal(0, cv * 0.6, size=(n, 1))
            # Deriva que vai acumulando: quanto mais longe no tempo, mais incerto.
            passeio = np.cumsum(rng.normal(0, deriva, size=(n, t)), axis=1)
            # Sobe e desce normal de um mês pro outro.
            ruido_mes = rng.normal(0, cv * 0.5, size=(n, t))
            d[chave] = d[chave] * np.exp(nivel + passeio + ruido_mes)
        d["churn"] = np.minimum(d["churn"], 0.5)
        out = rodar(base0, tipo, d)
        for k in res:
            res[k][s] = out[k]
        cac_sim[s] = d["cac"]
    res["cac"] = cac_sim
    return meses, res


# ------------------------------------------------------------------ backtest
def backtest(real, parceiros, sazonal, h=3, inicio="2025-03-01", fim=None):
    """
    Teste do forecast no passado: em cada mês de origem, monta as premissas só com o que se
    sabia até ali, projeta h meses e compara com o que aconteceu.
    """
    fim = fim or (real.mes.max() - pd.DateOffset(months=h))
    linhas = []
    for origem in pd.date_range(inicio, fim, freq="MS"):
        # Fingindo que estou nesse mês do passado: só uso o que já tinha acontecido até ali.
        hist = real[real.mes <= origem]
        prem = premissas_recentes(hist, [p for p in parceiros if p in set(hist.parceiro)], origem, sazonal)
        meses, out = forecast(hist, prem, origem, h, sazonal)
        # Comparando a previsão de 3 meses à frente com o que aconteceu de verdade.
        alvo = meses[-1]
        verdade = real[real.mes == alvo]
        linhas.append(dict(
            origem=origem, alvo=alvo,
            receita_prev=out["receita"][:, -1].sum(), receita_real=verdade.receita_mil.sum(),
            base_prev=out["base"][:, -1].sum(), base_real=verdade.base_final_mil.sum(),
            mc_prev=out["mc"][:, -1].sum(), mc_real=verdade.mc_mil.sum(),
        ))
    bt = pd.DataFrame(linhas)
    for k in ["receita", "base", "mc"]:
        bt[f"erro_{k}"] = (bt[f"{k}_prev"] / bt[f"{k}_real"] - 1) * 100
    return bt


# ------------------------------------------------------------------ sensibilidade
def sensibilidade(real, prem, ate, sazonal, meses_a_frente=12, choque=0.10, custo_fixo=5200):
    """Resultado operacional dos próximos meses com cada alavanca ±choque, uma de cada vez."""
    meses, base = forecast(real, prem, ate, meses_a_frente, sazonal)
    # Resultado operacional de referência, sem mexer em nada.
    ref = base["mc"].sum() - custo_fixo * meses_a_frente
    linhas = []
    # Mexendo uma alavanca por vez, pra cima e pra baixo, com as outras paradas.
    for alav in ["ativ", "churn", "preco", "custo", "cac", "verba", "cresc", "fixo"]:
        vals = {}
        for sinal in (-1, 1):
            if alav == "fixo":
                vals[sinal] = base["mc"].sum() - custo_fixo * (1 + sinal * choque) * meses_a_frente
                continue
            p2 = prem.copy()
            p2[alav] = p2[alav] * (1 + sinal * choque)
            _, out = forecast(real, p2, ate, meses_a_frente, sazonal)
            vals[sinal] = out["mc"].sum() - custo_fixo * meses_a_frente
        linhas.append(dict(alavanca=alav, menos=vals[-1] - ref, mais=vals[1] - ref))
    t = pd.DataFrame(linhas)
    t["amplitude"] = (t.mais - t.menos).abs()
    return t.sort_values("amplitude"), ref


# ------------------------------------------------------------------ parceiros
def rentabilidade(real, ate, meses=12):
    ini = pd.Timestamp(ate) - pd.DateOffset(months=meses - 1)
    r = real[(real.mes >= ini) & (real.mes <= ate)]
    g = r.groupby("parceiro").agg(
        receita=("receita_mil", "sum"), custo=("custo_conteudo_mil", "sum"), verba=("verba_mkt_mil", "sum"),
        mc=("mc_mil", "sum"), base_media=("base_final_mil", "mean"),
        ativacoes=("ativacoes_mil", "sum"), cancelamentos=("cancelamentos_mil", "sum"),
        base_ini=("base_inicial_mil", "sum"), meses=("mes", "count"))
    g["mc_pct"] = g.mc / g.receita * 100
    g["churn"] = g.cancelamentos / g.base_ini * 100
    # Quanto de margem cada assinante deixa por mês, em reais.
    g["mc_assinante_mes"] = g.mc / g.base_media / g.meses          # R$ por assinante por mês
    # LTV = margem por mês × tempo médio de vida (1 ÷ churn). Churn de 5% = vida média de 20 meses.
    g["ltv"] = g.mc_assinante_mes / (g.churn / 100)               # R$ de MC na vida média do assinante
    return g.sort_values("mc", ascending=False)


# ------------------------------------------------------------------ novo país
def business_case(p, meses=36, rng=None, n_sim=0):
    """
    Fluxo de caixa mensal da entrada num país novo (R$ mil).
    p: elegivel, ativ, churn, tarifa, custo, investimento, fixo, rampa, desconto_aa.
    Com n_sim > 0, sorteia ativação, churn e tarifa dentro das faixas e devolve as simulações.
    """
    def um(ativ, churn, tarifa):
        base, caixa, linhas = 0.0, -p["investimento"], []
        # Convertendo a taxa de desconto anual em mensal.
        taxa_m = (1 + p["desconto_aa"]) ** (1 / 12) - 1
        vpl = -p["investimento"]
        payback = None
        for m in range(1, meses + 1):
            # Os parceiros não entram todos no mês 1: a base elegível vai abrindo aos poucos até o fim da rampa.
            rampa = min(1.0, m / max(1, p["rampa"]))
            elegivel = p["elegivel"] * rampa
            base = base * (1 - churn) + elegivel * ativ
            # Fluxo do mês = margem dos assinantes - custo fixo local. O investimento já entrou negativo no mês 0.
            fluxo = base * (tarifa - p["custo"]) - p["fixo"]
            caixa += fluxo
            vpl += fluxo / (1 + taxa_m) ** m
            # Payback = primeiro mês em que o caixa acumulado volta a ficar positivo.
            if payback is None and caixa >= 0:
                payback = m
            linhas.append(dict(mes=m, base=base, fluxo=fluxo, caixa=caixa))
        return pd.DataFrame(linhas), vpl, payback

    det = um(p["ativ"], p["churn"], p["tarifa"])
    if not n_sim:
        return det
    rng = rng or np.random.default_rng(11)
    sims = []
    for _ in range(n_sim):
        # Sorteando ativação, churn e tarifa dentro da faixa de incerteza e refazendo a conta.
        a = p["ativ"] * rng.uniform(1 - p["faixa_ativ"], 1 + p["faixa_ativ"])
        c = p["churn"] * rng.uniform(1 - p["faixa_churn"], 1 + p["faixa_churn"])
        t = p["tarifa"] * rng.uniform(1 - p["faixa_tarifa"], 1 + p["faixa_tarifa"])
        _, vpl, pb = um(a, c, t)
        sims.append(dict(vpl=vpl, payback=pb if pb is not None else np.nan))
    return det, pd.DataFrame(sims)
