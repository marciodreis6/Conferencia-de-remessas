# Conferencia Logistica

MVP local para conferencia de remessas. A aplicacao recebe bases diarias e varios
arquivos TXT, cruza produto, quantidade, lote e validade, aplica regras de shelf
life por cliente e exporta um historico XLSX.

## Executar

```powershell
.\run.ps1
```

Abra `http://localhost:8000`.

## Fluxo rapido

1. Na aba **Bases diarias**, importe o relatorio da fabrica, o detalhamento de
   remessas, os itens bloqueados e a base inicial de shelf life.
2. Na aba **Shelf life**, confira ou altere os parametros dos clientes.
3. Na aba **Processar TXTs**, carregue um ou varios arquivos gerados pelo leitor.
4. Consulte os resultados na aba **Historico** e baixe o XLSX.

## Formatos aceitos

As bases aceitam `.xlsx`, `.csv` e `.txt` delimitados. O TXT do leitor nao
possui cabecalho: cada linha contem data, hora, chave do palete e quantidade.
O importador reconhece aliases comuns para os cabecalhos das planilhas.

## Estrutura

- `app/server.py`: servidor HTTP e rotas.
- `app/db.py`: persistencia SQLite e historico.
- `app/parsers.py`: leitura de TXT, CSV e XLSX.
- `app/validation.py`: regras de conferencia.
- `app/service.py`: coordenacao do fluxo.
- `app/xlsx_writer.py`: exportacao XLSX.
- `web/`: interface web.
