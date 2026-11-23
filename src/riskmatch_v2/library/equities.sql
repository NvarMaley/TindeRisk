-- Vendor rows may repeat monthly fields for several distributions.
CREATE TEMP TABLE raw AS
SELECT PERMNO::INTEGER permno, PERMCO::INTEGER permco, Ticker ticker, CUSIP9 cusip,
       IssuerNm issuer, PrimaryExch exchange, SICCD sector, USIncFlg country_flag,
       SecurityType security_type, SecuritySubType subtype, ShareType share_type,
       TradingStatusFlg trading, CAST(SecInfoStartDt AS DATE) id_from,
       CAST(SecInfoEndDt AS DATE) id_to, CAST(SecurityBegDt AS DATE) security_from,
       CAST(SecurityEndDt AS DATE) security_end, CAST(MthCalDt AS DATE) AS day,
       TRY_CAST(MthPrcDt AS DATE) price_day, TRY_CAST(MthPrevDt AS DATE) previous_day,
       TRY_CAST(MthPrc AS DOUBLE) price, TRY_CAST(MthRet AS DOUBLE) local_return,
       TRY_CAST(MthVol AS DOUBLE) volume, MthDelFlg del_flag, MthRetFlg return_flag,
       DelPaymentType exit_payment, TRY_CAST(DisExDt AS DATE) ex_date,
       TRY_CAST(DisDivAmt AS DOUBLE) dividend, TRY_CAST(DisFacShr AS DOUBLE) share_factor,
       DisSeqNbr event_sequence, DisType distribution_type, DisPaymentType payment_type,
       TRY_CAST(DisPayDt AS DATE) payment_date, DelReasonType exit_reason
FROM read_csv($raw_file, header=true, all_varchar=true);
CREATE TEMP TABLE identifiers AS
SELECT DISTINCT permno,permco,ticker,cusip,issuer,exchange,sector,country_flag,security_type,subtype,
       share_type,trading,id_from,id_to,security_from,security_end FROM raw;
CREATE TEMP TABLE candidate_rows AS
SELECT DISTINCT permno,day,previous_day,price_day,price,local_return,volume,del_flag,return_flag,
       permco,ticker,cusip,issuer,exchange,sector,trading,country_flag,security_type,subtype,share_type,
       exit_payment
FROM raw WHERE day BETWEEN id_from AND id_to;
CREATE TEMP TABLE months AS
SELECT *, count(*) OVER (PARTITION BY permno, day) AS variants FROM candidate_rows;
