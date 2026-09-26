# Metodologia

## 1. Aquisição

Os dados são obtidos diretamente de páginas oficiais da ANP. O script de extração identifica os links da publicação semanal mais recente e preserva os arquivos originais.

## 2. Camada raw

A camada `data/raw/` contém os arquivos exatamente como recebidos. Nenhuma transformação é permitida nesta etapa.

## 3. Inspeção

Antes do tratamento são verificados:

- formato do arquivo;
- planilhas disponíveis, quando aplicável;
- quantidade de linhas e colunas;
- nomes das colunas;
- tipos inferidos;
- valores ausentes;
- duplicidades potenciais.

## 4. Transformação

A etapa seguinte deverá padronizar nomes de colunas, datas, textos, identificadores geográficos e valores monetários. Regras de transformação serão registradas em código e documentadas.

## 5. Qualidade

Validações previstas:

- preços não negativos;
- datas válidas;
- UF dentro do domínio oficial;
- produto dentro do domínio observado;
- consistência entre município e UF;
- identificação de duplicidades;
- registro de nulos por coluna;
- análise de outliers sem remoção automática.

Valores extremos não serão descartados sem justificativa documentada.

## 6. Modelo analítico

A camada SQL utilizará uma tabela fato de preços e dimensões para data, produto, localidade, posto e bandeira. O modelo será refinado após a inspeção do schema real das fontes.

## 7. Indicadores

Indicadores iniciais:

- média;
- mediana;
- mínimo;
- máximo;
- amplitude;
- desvio padrão;
- coeficiente de variação;
- variação absoluta e percentual;
- quantidade de observações;
- quantidade de estabelecimentos pesquisados.

## 8. Reprodutibilidade

Nenhum resultado analítico será digitado manualmente. Tabelas, métricas e visuais devem ser derivados dos dados processados pelo pipeline.
