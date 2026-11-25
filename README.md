# Janus — plano, forecast, OKRs e business case

O deus das duas faces: uma olha o que já aconteceu, a outra o que vem pela frente.

🌐 Português e inglês: botão PT/EN no topo da barra lateral (ou `?lang=en` na URL).

Simulador de planejamento para um negócio de **assinatura B2B2C**: a Lumina, empresa fictícia, vende um app de
conteúdo digital por parceiros (operadoras, banco, varejo, fintech), que pagam uma tarifa por assinante ativo, e
direto no app. Todo mês a pergunta é a mesma: **o plano continua de pé? O que precisa ser ajustado? Onde apostar?**

A base é **sintética**, com desvios plantados em 2026 (queda de ativação num parceiro, churn piorando em outro,
reajuste de tarifa, CAC subindo), pra dar pra conferir se a leitura do mês encontra o que aconteceu.

## O que tem
- **Leitura do mês:** o plano continua de pé? Chance de bater o ano, aterrissagem, ponte da margem plano → realizado
  por alavanca e mapa parceiro × alavanca, com sugestões do que ajustar.
- **Plano e cenários:** forecast de 12 a 36 meses em cenário otimista, base, pessimista e um personalizado, com a
  faixa provável (P10–P90) de 600 simulações.
- **Sensibilidade:** tornado com o efeito de cada alavanca no resultado dos próximos 12 meses.
- **OKRs:** cards de farol com a chance de bater cada KR, metas editáveis e checklist de KR bem escrito.
- **Parceiros:** rentabilidade, LTV e simulador de renegociação de tarifa e churn.
- **Novo país:** business case do mercado à base em regime, caixa acumulado, VPL, payback, chance de dar certo e mapa
  de payback por ativação × tarifa.
- **Como funciona** (com backtest do forecast) e **Glossário**, escritos pra quem não é da área, com exemplos.

## Modelo
- Uma conta só, mês a mês e por parceiro: `base = base anterior + ativações − cancelamentos`;
  ativações = elegíveis × taxa (parceiros) ou verba ÷ CAC (direto); margem = receita − custo de conteúdo − verba.
- Premissas recentes: média dos últimos 12 meses com meia-vida de 3 meses; ativação dessazonalizada.
- Tendência amortecida: ativação, churn ou CAC com tendência clara nos últimos 8 meses (teste t ≥ 3) partem do
  último mês e seguem a inclinação, que perde 20% de força por mês; mudança de degrau não vira tendência.
- Monte Carlo: desvio persistente do tamanho da variação histórica + deriva que cresce com o horizonte.
- Ponte de variação por substituição sequencial (as peças somam exatamente a diferença).
- Backtest: forecast 3 meses à frente refeito em cada mês do passado.

## Rodar
Windows: dois cliques em `rodar_janus.bat`.
Outros: `pip install -r requirements.txt` e `streamlit run app.py`.

Para regerar a base: `python dados/gerar_base.py`.

## Estrutura
```
app.py                 app Streamlit
janus/modelo.py        a conta, plano, ponte, forecast, Monte Carlo, sensibilidade, business case
janus/i18n.py          português e inglês
dados/gerar_base.py    gerador da base sintética
dados/*.csv            realizado mensal e premissas do plano 2026
assets/                imagens
```

## English

**Janus — plan, forecast, OKRs and business case.** A planning simulator for a **B2B2C subscription** business: Lumina,
a fictional company, sells a digital-content app through partners (telcos, a bank, a retailer, a fintech) that pay a fee
per active subscriber, and directly in the app. Tabs: monthly review (is the plan still standing? variance bridge by lever
and partner), plan & scenarios (12–36 month forecast with P10–P90 band), sensitivity, OKRs (traffic-light cards with the
chance of hitting each KR), partners (profitability, LTV, renegotiation simulator), new country (market sizing, NPV,
payback, chance of success), how it works (with forecast backtest) and glossary. **Synthetic data** with deviations
planted in 2026. The whole app switches to English with the PT/EN toggle in the sidebar (or `?lang=en`).

Gabriela Gatti Rodrigues · [Portfólio](https://gabigattirodrigues.github.io/) · [LinkedIn](https://linkedin.com/in/gabriela-gatti-rodrigues)
