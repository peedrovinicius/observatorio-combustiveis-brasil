# Fontes de dados

## Fonte principal

**Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)**

### Levantamento de Preços de Combustíveis

Página oficial:

https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas

Uso no projeto:

- referência para as publicações semanais;
- conferência da cobertura temporal;
- validação das séries publicadas pela ANP.

### Série histórica do levantamento de preços

https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos

Uso no projeto:

- série semanal de Brasil;
- regiões;
- estados;
- municípios em 2026.

Os arquivos são validados pelo conteúdo antes de serem aceitos como XLSX. Uma resposta HTML intermediária não é salva como planilha.

A série histórica é atualizada como um lote único. Brasil, regiões, estados e municípios são baixados e validados antes de qualquer substituição local.

Depois da validação de todo o lote, os arquivos anteriores e o `history_manifest.json` são movidos para backup temporário. As novas planilhas e o novo manifesto são instalados juntos. Se qualquer instalação falhar, todos os arquivos já trocados naquela execução são removidos e o snapshot anterior completo é restaurado.

### Série Histórica de Preços de Combustíveis e de GLP

https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis

Uso no projeto:

- observações de preço por estabelecimento;
- produto e unidade de medida;
- CNPJ e identificação do posto;
- bandeira;
- distribuição municipal de preços.

O downloader identifica CSV, ZIP e XLSX pelo conteúdo real do arquivo. Isso cobre respostas do portal com `application/octet-stream` e impede que páginas HTML sejam tratadas como dados.

Quando uma publicação já existe localmente, a nova versão é preparada em staging antes de qualquer alteração no dataset anterior. Para ZIP, todos os CSVs internos são extraídos e validados no staging. Nomes de CSV que colidiriam em sistemas sem diferenciação entre maiúsculas e minúsculas também são rejeitados.

Somente depois de toda a preparação ter sucesso, a coleção completa descoberta para 2026 é publicada como um único lote lógico junto de `data/raw/open_data/manifest.json`. Nenhum dataset é substituído localmente enquanto ainda existem downloads pendentes.

Os artefatos anteriores de todos os datasets envolvidos e o manifesto são movidos para backup temporário. Se qualquer instalação falhar, o processo remove os artefatos novos já instalados e restaura integralmente o snapshot anterior.

A descoberta exige cobertura do primeiro semestre de combustíveis automotivos e presença das famílias diesel/GNV e etanol/gasolina. Identidades lógicas duplicadas ou a reutilização da mesma URL para datasets distintos são bloqueadas.

A substituição cobre mudanças entre CSV e ZIP, incluindo diretórios de extração. Arquivos de outros datasets são preservados.

### Cadastro de revendedores varejistas

https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos

Possível uso futuro:

- enriquecimento cadastral;
- validação complementar de estabelecimentos;
- atributos não presentes na série de preços.

Essa fonte não é necessária para executar o pipeline atual.

## Rastreabilidade

Todo arquivo aceito pelo pipeline mantém registro de:

- URL da página oficial;
- URL descoberta;
- URL final do arquivo;
- data e hora da coleta em UTC;
- nome do arquivo salvo;
- formato detectado pelo conteúdo;
- tipo de conteúdo HTTP informado;
- tamanho em bytes;
- hash SHA-256.

Manifestos:

```text
data/raw/history_manifest.json
data/raw/open_data/manifest.json
```

## Política de dados

Os arquivos brutos não são modificados.

Qualquer limpeza, conversão de tipos, padronização, deduplicação ou criação de colunas produz saídas em `data/processed/` e relatórios em `reports/`.

A camada por posto também registra exclusões e sobreposições em:

```text
reports/station_ingestion_audit_2026.json
```
