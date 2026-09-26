# Fontes de dados

## Fonte principal

**Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)**

### Levantamento de Preços de Combustíveis

Página oficial:

https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas

Uso no projeto:

- preços médios semanais;
- preços por posto revendedor;
- combustíveis automotivos e GLP P13;
- recortes geográficos publicados pela ANP.

### Série histórica do levantamento de preços

https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos

Uso planejado:

- construção de séries temporais;
- comparações anuais e mensais;
- análise por Brasil, região, UF e município.

### Cadastro de revendedores varejistas

https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos

Uso planejado:

- enriquecimento cadastral de postos;
- análise por bandeira e localização;
- validações de estabelecimentos em operação.

## Rastreabilidade

Todo arquivo baixado pelo pipeline deve manter registro de:

- URL da página oficial;
- URL final do arquivo;
- data e hora da coleta em UTC;
- nome do arquivo salvo;
- tamanho em bytes;
- hash SHA-256.

O registro é salvo em `data/raw/manifest.json`.

## Política de dados

Os arquivos brutos não devem ser modificados. Qualquer limpeza, conversão de tipos, padronização ou criação de colunas deve produzir novos arquivos em `data/processed/`.
