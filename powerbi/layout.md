# Especificação visual do dashboard

## Direção visual

O dashboard deve transmitir clareza, confiabilidade e leitura rápida.

Princípios:

- fundo claro;
- cartões brancos;
- tipografia simples;
- poucos elementos por página;
- títulos curtos;
- filtros alinhados no topo;
- hierarquia visual consistente;
- evitar excesso de cores;
- não usar elementos decorativos sem função analítica.

O tema oficial está em `powerbi/theme.json`.

## Página 1: Visão Geral

Objetivo: responder rapidamente qual é o cenário atual.

### Filtros

- produto;
- unidade de medida;
- nível geográfico;
- localidade.

### Linha superior

Cinco cartões:

1. preço atual;
2. variação semanal;
3. preço mínimo;
4. preço máximo;
5. postos pesquisados.

### Corpo

Esquerda:
- linha de evolução semanal por produto.

Direita:
- barras com comparação entre regiões ou UFs.

Rodapé:
- tabela compacta com maiores e menores preços.

## Página 2: Geografia

Objetivo: mostrar onde estão as maiores diferenças.

Visuais:

- mapa por UF;
- ranking de UFs;
- ranking de municípios;
- amplitude;
- coeficiente de variação.

Filtros:

- produto;
- unidade de medida;
- UF;
- município;
- período.

## Página 3: Tendência

Objetivo: explicar comportamento no tempo.

Visuais:

- evolução semanal;
- média das semanas por mês;
- variação mensal derivada;
- mínimo e máximo do período.

Regra:

A média mensal derivada deve estar explicitamente identificada como cálculo do projeto.

## Página 4: Mercado por Posto

Objetivo: explorar distribuição e heterogeneidade dos preços observados.

Visuais:

- histograma de preço;
- mediana;
- preço médio por bandeira;
- quantidade de revendas;
- menores preços observados;
- maiores preços observados;
- dispersão por município.

Usar somente a tabela fato por posto.

## Página 5: Etanol x Gasolina

Objetivo: comparar os dois combustíveis por município.

Visuais:

- relação etanol/gasolina;
- dispersão entre preços;
- ranking por município;
- filtro por UF;
- filtro por unidade de medida.

A página apresenta a razão observada. Qualquer interpretação de vantagem econômica deve ter hipótese explícita.

## Regra de série analítica

Medidas agregadas de preço devem operar em uma única combinação de produto, unidade de medida, nível geográfico e localidade. Comparações entre localidades devem ocorrer por categorias do visual, não por média aritmética entre agregados oficiais.

Na camada por posto, produto e unidade de medida também definem conjuntamente a série. A última data de coleta é obtida para a série inteira e não separadamente por cada município ou bandeira.

## Convenções

### Casas decimais

Preço:
- 2 casas decimais na interface;
- precisão original preservada na camada de dados.

Percentual:
- 2 casas decimais.

### Ordenação

Rankings:
- preço maior para menor quando a pergunta for "mais caro";
- preço menor para maior quando a pergunta for "mais barato".

### Tooltips

Sempre que possível incluir:

- período;
- produto;
- localidade;
- quantidade de postos;
- preço mínimo;
- preço máximo;
- fonte.

## Acessibilidade

- não depender somente de cor;
- usar rótulos claros;
- manter contraste suficiente;
- evitar textos pequenos;
- utilizar símbolos ou posição para complementar diferenças visuais;
- validar leitura em telas de notebook.

## Resolução alvo

Priorizar layout 16:9, com boa leitura em 1920 x 1080 e funcionamento aceitável em notebooks menores.
