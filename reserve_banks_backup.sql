--
-- PostgreSQL database dump
--

\restrict YkOoaIcw4AGwuNvxFvYOGIeB3xhqHBqcsuO7fN7t0R7u5I0xccYQbQtpYBlnwTo

-- Dumped from database version 18.2
-- Dumped by pg_dump version 18.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bank_debts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bank_debts (
    id integer NOT NULL,
    debtor_bank_id integer NOT NULL,
    creditor_currency character varying(8) NOT NULL,
    amount_owed double precision NOT NULL,
    created_at timestamp without time zone,
    last_settled_at timestamp without time zone,
    is_settled boolean
);


--
-- Name: bank_debts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bank_debts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bank_debts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bank_debts_id_seq OWNED BY public.bank_debts.id;


--
-- Name: bank_reserve_balances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bank_reserve_balances (
    id integer NOT NULL,
    bank_id integer NOT NULL,
    currency_code character varying(8) NOT NULL,
    balance double precision,
    total_received double precision,
    total_paid double precision,
    updated_at timestamp without time zone
);


--
-- Name: bank_reserve_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bank_reserve_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bank_reserve_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bank_reserve_balances_id_seq OWNED BY public.bank_reserve_balances.id;


--
-- Name: bond_yield_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bond_yield_history (
    id integer NOT NULL,
    bank_id integer NOT NULL,
    yield_rate double precision NOT NULL,
    usd_per_unit double precision NOT NULL,
    recorded_at timestamp without time zone
);


--
-- Name: bond_yield_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bond_yield_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bond_yield_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bond_yield_history_id_seq OWNED BY public.bond_yield_history.id;


--
-- Name: forex_trades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.forex_trades (
    id integer NOT NULL,
    player_id integer,
    from_currency character varying(8) NOT NULL,
    to_currency character varying(8) NOT NULL,
    amount_from double precision NOT NULL,
    amount_to double precision NOT NULL,
    exchange_rate double precision NOT NULL,
    fee_usd double precision,
    executed_at timestamp without time zone
);


--
-- Name: forex_trades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.forex_trades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: forex_trades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.forex_trades_id_seq OWNED BY public.forex_trades.id;


--
-- Name: interbank_trades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.interbank_trades (
    id integer NOT NULL,
    buyer_bank_code character varying(8) NOT NULL,
    seller_bank_code character varying(8) NOT NULL,
    bond_currency character varying(8) NOT NULL,
    face_value_usd double precision NOT NULL,
    consideration_curr character varying(8) NOT NULL,
    consideration_amount double precision NOT NULL,
    trigger character varying,
    executed_at timestamp without time zone
);


--
-- Name: interbank_trades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.interbank_trades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: interbank_trades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.interbank_trades_id_seq OWNED BY public.interbank_trades.id;


--
-- Name: player_currency_balances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_currency_balances (
    id integer NOT NULL,
    player_id integer NOT NULL,
    currency_code character varying(8) NOT NULL,
    balance double precision,
    total_earned double precision,
    total_spent double precision,
    updated_at timestamp without time zone
);


--
-- Name: player_currency_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_currency_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: player_currency_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_currency_balances_id_seq OWNED BY public.player_currency_balances.id;


--
-- Name: player_legal_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.player_legal_tenders (
    player_id integer NOT NULL,
    currency_code character varying(8) NOT NULL,
    changed_at timestamp without time zone
);


--
-- Name: player_legal_tenders_player_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.player_legal_tenders_player_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: player_legal_tenders_player_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.player_legal_tenders_player_id_seq OWNED BY public.player_legal_tenders.player_id;


--
-- Name: reserve_bank_bonds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reserve_bank_bonds (
    id integer NOT NULL,
    bank_id integer NOT NULL,
    holder_player_id integer NOT NULL,
    face_value_wsc double precision NOT NULL,
    purchase_yield double precision NOT NULL,
    maturity_days integer NOT NULL,
    purchased_at timestamp without time zone,
    matures_at timestamp without time zone NOT NULL,
    interest_accrued double precision,
    total_interest_paid double precision,
    status character varying
);


--
-- Name: reserve_bank_bonds_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reserve_bank_bonds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reserve_bank_bonds_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reserve_bank_bonds_id_seq OWNED BY public.reserve_bank_bonds.id;


--
-- Name: state_reserve_banks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.state_reserve_banks (
    id integer NOT NULL,
    currency_code character varying(8) NOT NULL,
    currency_name character varying(80) NOT NULL,
    currency_symbol character varying(8) NOT NULL,
    flag_emoji character varying(8) NOT NULL,
    yield_rate double precision,
    min_yield double precision,
    max_yield double precision,
    usd_per_unit double precision,
    net_demand_wsc double precision,
    total_bonds_issued integer,
    total_face_value_wsc double precision,
    total_interest_paid double precision,
    total_forex_volume double precision,
    founded_at timestamp without time zone
);


--
-- Name: state_reserve_banks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.state_reserve_banks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: state_reserve_banks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.state_reserve_banks_id_seq OWNED BY public.state_reserve_banks.id;


--
-- Name: bank_debts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_debts ALTER COLUMN id SET DEFAULT nextval('public.bank_debts_id_seq'::regclass);


--
-- Name: bank_reserve_balances id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_reserve_balances ALTER COLUMN id SET DEFAULT nextval('public.bank_reserve_balances_id_seq'::regclass);


--
-- Name: bond_yield_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bond_yield_history ALTER COLUMN id SET DEFAULT nextval('public.bond_yield_history_id_seq'::regclass);


--
-- Name: forex_trades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.forex_trades ALTER COLUMN id SET DEFAULT nextval('public.forex_trades_id_seq'::regclass);


--
-- Name: interbank_trades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.interbank_trades ALTER COLUMN id SET DEFAULT nextval('public.interbank_trades_id_seq'::regclass);


--
-- Name: player_currency_balances id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_currency_balances ALTER COLUMN id SET DEFAULT nextval('public.player_currency_balances_id_seq'::regclass);


--
-- Name: player_legal_tenders player_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_legal_tenders ALTER COLUMN player_id SET DEFAULT nextval('public.player_legal_tenders_player_id_seq'::regclass);


--
-- Name: reserve_bank_bonds id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserve_bank_bonds ALTER COLUMN id SET DEFAULT nextval('public.reserve_bank_bonds_id_seq'::regclass);


--
-- Name: state_reserve_banks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.state_reserve_banks ALTER COLUMN id SET DEFAULT nextval('public.state_reserve_banks_id_seq'::regclass);


--
-- Data for Name: bank_debts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bank_debts (id, debtor_bank_id, creditor_currency, amount_owed, created_at, last_settled_at, is_settled) FROM stdin;
\.


--
-- Data for Name: bank_reserve_balances; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bank_reserve_balances (id, bank_id, currency_code, balance, total_received, total_paid, updated_at) FROM stdin;
1	1	USD	38480.70654330465	38480.70654330465	0	2026-02-25 20:36:47.121544
2	1	JPY	11486.778072628253	11486.778072628253	0	2026-02-25 20:36:47.122598
\.


--
-- Data for Name: bond_yield_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bond_yield_history (id, bank_id, yield_rate, usd_per_unit, recorded_at) FROM stdin;
1	1	0.001	0.0067	2026-02-24 19:58:27.540297
2	2	0.08	0.058	2026-02-24 19:58:27.540297
3	3	0.045	1.27	2026-02-24 19:58:27.540297
4	4	0.015	1.12	2026-02-24 19:58:27.540297
5	5	0.025	0.138	2026-02-24 19:58:27.540297
6	6	0.03	1.08	2026-02-24 19:58:27.540297
7	7	0.065	0.012	2026-02-24 19:58:27.540297
8	8	0.16	0.011	2026-02-24 19:58:27.540297
9	1	0.001	0.0067	2026-02-24 21:03:31.678015
10	2	0.08	0.058	2026-02-24 21:03:31.678015
11	3	0.045	1.27	2026-02-24 21:03:31.678015
12	4	0.015	1.12	2026-02-24 21:03:31.678015
13	5	0.025	0.138	2026-02-24 21:03:31.678015
14	6	0.03	1.08	2026-02-24 21:03:31.678015
15	7	0.065	0.012	2026-02-24 21:03:31.678015
16	8	0.16	0.011	2026-02-24 21:03:31.678015
17	1	0.001	0.0067	2026-02-24 22:42:56.008397
18	2	0.08	0.058	2026-02-24 22:42:56.008397
19	3	0.045	1.27	2026-02-24 22:42:56.008397
20	4	0.015	1.12	2026-02-24 22:42:56.008397
21	5	0.025	0.138	2026-02-24 22:42:56.008397
22	6	0.03	1.08	2026-02-24 22:42:56.008397
23	7	0.065	0.012	2026-02-24 22:42:56.008397
24	8	0.16	0.011	2026-02-24 22:42:56.008397
25	1	0.001	0.0067	2026-02-25 01:47:58.539333
26	2	0.08	0.058	2026-02-25 01:47:58.539333
27	3	0.045	1.27	2026-02-25 01:47:58.539333
28	4	0.015	1.12	2026-02-25 01:47:58.539333
29	5	0.025	0.138	2026-02-25 01:47:58.539333
30	6	0.03	1.08	2026-02-25 01:47:58.539333
31	7	0.065	0.012	2026-02-25 01:47:58.539333
32	8	0.16	0.011	2026-02-25 01:47:58.539333
33	1	0.001	0.0067	2026-02-25 02:53:29.08652
34	2	0.08	0.058	2026-02-25 02:53:29.08652
35	3	0.045	1.27	2026-02-25 02:53:29.08652
36	4	0.015	1.12	2026-02-25 02:53:29.08652
37	5	0.025	0.138	2026-02-25 02:53:29.08652
38	6	0.03	1.08	2026-02-25 02:53:29.08652
39	7	0.065	0.012	2026-02-25 02:53:29.08652
40	8	0.16	0.011	2026-02-25 02:53:29.08652
41	1	0.001	0.0067	2026-02-25 04:16:49.56654
42	2	0.08	0.058	2026-02-25 04:16:49.56654
43	3	0.045	1.27	2026-02-25 04:16:49.56654
44	4	0.015	1.12	2026-02-25 04:16:49.56654
45	5	0.025	0.138	2026-02-25 04:16:49.56654
46	6	0.03	1.08	2026-02-25 04:16:49.56654
47	7	0.065	0.012	2026-02-25 04:16:49.56654
48	8	0.16	0.011	2026-02-25 04:16:49.56654
49	1	0.001	0.0067	2026-02-25 05:22:26.400188
50	2	0.08	0.058	2026-02-25 05:22:26.400188
51	3	0.045	1.27	2026-02-25 05:22:26.400188
52	4	0.015	1.12	2026-02-25 05:22:26.400188
53	5	0.025	0.138	2026-02-25 05:22:26.400188
54	6	0.03	1.08	2026-02-25 05:22:26.400188
55	7	0.065	0.012	2026-02-25 05:22:26.400188
56	8	0.16	0.011	2026-02-25 05:22:26.400188
57	1	0.001	0.0067	2026-02-25 08:34:21.329483
58	2	0.08	0.058	2026-02-25 08:34:21.329483
59	3	0.045	1.27	2026-02-25 08:34:21.329483
60	4	0.015	1.12	2026-02-25 08:34:21.329483
61	5	0.025	0.138	2026-02-25 08:34:21.329483
62	6	0.03	1.08	2026-02-25 08:34:21.329483
63	7	0.065	0.012	2026-02-25 08:34:21.329483
64	8	0.16	0.011	2026-02-25 08:34:21.329483
65	1	0.001	0.0067	2026-02-25 09:41:39.47873
66	2	0.08	0.058	2026-02-25 09:41:39.47873
67	3	0.045	1.27	2026-02-25 09:41:39.47873
68	4	0.015	1.12	2026-02-25 09:41:39.47873
69	5	0.025	0.138	2026-02-25 09:41:39.47873
70	6	0.03	1.08	2026-02-25 09:41:39.47873
71	7	0.065	0.012	2026-02-25 09:41:39.47873
72	8	0.16	0.011	2026-02-25 09:41:39.47873
73	1	0.001	0.0067	2026-02-25 10:49:50.070134
74	2	0.08	0.058	2026-02-25 10:49:50.070134
75	3	0.045	1.27	2026-02-25 10:49:50.070134
76	4	0.015	1.12	2026-02-25 10:49:50.070134
77	5	0.025	0.138	2026-02-25 10:49:50.070134
78	6	0.03	1.08	2026-02-25 10:49:50.070134
79	7	0.065	0.012	2026-02-25 10:49:50.070134
80	8	0.16	0.011	2026-02-25 10:49:50.070134
81	1	0.001	0.0067	2026-02-25 11:58:09.297206
82	2	0.08	0.058	2026-02-25 11:58:09.297206
83	3	0.045	1.27	2026-02-25 11:58:09.297206
84	4	0.015	1.12	2026-02-25 11:58:09.297206
85	5	0.025	0.138	2026-02-25 11:58:09.297206
86	6	0.03	1.08	2026-02-25 11:58:09.297206
87	7	0.065	0.012	2026-02-25 11:58:09.297206
88	8	0.16	0.011	2026-02-25 11:58:09.297206
89	1	0.001	0.0067	2026-02-25 13:06:25.349612
90	2	0.08	0.058	2026-02-25 13:06:25.349612
91	3	0.045	1.27	2026-02-25 13:06:25.349612
92	4	0.015	1.12	2026-02-25 13:06:25.349612
93	5	0.025	0.138	2026-02-25 13:06:25.349612
94	6	0.03	1.08	2026-02-25 13:06:25.349612
95	7	0.065	0.012	2026-02-25 13:06:25.349612
96	8	0.16	0.011	2026-02-25 13:06:25.349612
97	1	0.001	0.0067	2026-02-25 14:14:52.340423
98	2	0.08	0.058	2026-02-25 14:14:52.340423
99	3	0.045	1.27	2026-02-25 14:14:52.340423
100	4	0.015	1.12	2026-02-25 14:14:52.340423
101	5	0.025	0.138	2026-02-25 14:14:52.340423
102	6	0.03	1.08	2026-02-25 14:14:52.340423
103	7	0.065	0.012	2026-02-25 14:14:52.340423
104	8	0.16	0.011	2026-02-25 14:14:52.340423
105	1	0.001	0.0067	2026-02-25 15:22:52.910389
106	2	0.08	0.058	2026-02-25 15:22:52.910389
107	3	0.045	1.27	2026-02-25 15:22:52.910389
108	4	0.015	1.12	2026-02-25 15:22:52.910389
109	5	0.025	0.138	2026-02-25 15:22:52.910389
110	6	0.03	1.08	2026-02-25 15:22:52.910389
111	7	0.065	0.012	2026-02-25 15:22:52.910389
112	8	0.16	0.011	2026-02-25 15:22:52.910389
\.


--
-- Data for Name: forex_trades; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.forex_trades (id, player_id, from_currency, to_currency, amount_from, amount_to, exchange_rate, fee_usd, executed_at) FROM stdin;
1	1	USD	JPY	2433.998556765289	362556.7999480236	149.2537313432836	4.867997113530578	2026-02-25 19:09:41.110155
2	1	USD	JPY	110.36228989852913	16439.039599810756	149.2537313432836	0.22072457979705823	2026-02-25 19:11:57.609671
3	1	USD	JPY	1126.9985537651446	167872.32188919617	149.2537313432836	2.253997107530289	2026-02-25 19:13:07.797591
4	1	USD	JPY	5983.998550765	891347.8438303686	149.2537313432836	11.967997101529999	2026-02-25 19:15:48.139546
5	1	USD	JPY	110.36177023225025	16438.962192803843	149.2537313432836	0.2207235404645005	2026-02-25 19:16:36.857243
6	1	USD	JPY	2482.9985477648547	369855.6045775112	149.2537313432836	4.96599709552971	2026-02-25 19:18:29.573783
7	1	USD	JPY	1064.9985447647093	158637.0966679373	149.2537313432836	2.1299970895294185	2026-02-25 19:21:10.192027
8	1	USD	JPY	6250.998541764564	931118.887265826	149.2537313432836	12.501997083529128	2026-02-25 19:23:51.806616
9	1	USD	JPY	2226.998538764418	331723.0659234163	149.2537313432836	4.453997077528836	2026-02-25 19:26:32.408078
10	1	USD	JPY	1235.9985357642715	184108.43861085715	149.2537313432836	2.471997071528543	2026-02-25 19:29:14.838002
11	1	USD	JPY	6091.998532764125	907435.0053281487	149.2537313432836	12.183997065528251	2026-02-25 20:25:16.243243
12	1	USD	JPY	2393.9985297639782	356598.58697081346	149.2537313432836	4.787997059527956	2026-02-25 20:31:23.07686
13	1	USD	JPY	1024.9985267638308	152678.88503138852	149.2537313432836	2.0499970535276617	2026-02-25 20:34:03.783441
14	1	USD	JPY	5941.998523763684	885091.7204053964	149.2537313432836	11.883997047527368	2026-02-25 20:36:47.125409
\.


--
-- Data for Name: interbank_trades; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.interbank_trades (id, buyer_bank_code, seller_bank_code, bond_currency, face_value_usd, consideration_curr, consideration_amount, trigger, executed_at) FROM stdin;
\.


--
-- Data for Name: player_currency_balances; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.player_currency_balances (id, player_id, currency_code, balance, total_earned, total_spent, updated_at) FROM stdin;
1	1	JPY	5731902.258241497	5731902.258241497	0	2026-02-25 20:36:47.123743
\.


--
-- Data for Name: player_legal_tenders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.player_legal_tenders (player_id, currency_code, changed_at) FROM stdin;
1	JPY	2026-02-25 00:38:10.859708
\.


--
-- Data for Name: reserve_bank_bonds; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reserve_bank_bonds (id, bank_id, holder_player_id, face_value_wsc, purchase_yield, maturity_days, purchased_at, matures_at, interest_accrued, total_interest_paid, status) FROM stdin;
1	1	1	500	0.001	30	2026-02-25 15:49:51.705763	2026-03-27 15:49:51.701736	0	0	active
2	8	1	500	0.16	30	2026-02-25 15:50:39.434073	2026-03-27 15:50:39.433142	0	0	active
3	2	1	500	0.08	30	2026-02-25 15:51:27.333125	2026-03-27 15:51:27.332137	0	0	active
\.


--
-- Data for Name: state_reserve_banks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.state_reserve_banks (id, currency_code, currency_name, currency_symbol, flag_emoji, yield_rate, min_yield, max_yield, usd_per_unit, net_demand_wsc, total_bonds_issued, total_face_value_wsc, total_interest_paid, total_forex_volume, founded_at) FROM stdin;
3	GBP	Wadsworth Bank of England	£	🇬🇧	0.045	-0.01	0.2	1.27	0	0	0	0	0	2026-02-24 17:48:59.674433
4	CHF	Wadsworth National Bank	Fr	🇨🇭	0.015	-0.02	0.1	1.12	0	0	0	0	0	2026-02-24 17:48:59.674435
5	CNY	People's Reserve Bank of Wadsworth	¥	🇨🇳	0.025	0.005	0.25	0.138	0	0	0	0	0	2026-02-24 17:48:59.674438
6	EUR	Wadsworth Central Bank	€	🇪🇺	0.03	-0.01	0.2	1.08	0	0	0	0	0	2026-02-24 17:48:59.67444
7	INR	Reserve Bank of Wadsworth India	₹	🇮🇳	0.065	0.03	0.35	0.012	0	0	0	0	0	2026-02-24 17:48:59.674443
8	RUB	Wadsworth Central Reserve Bank	₽	🇷🇺	0.16	0.05	0.99	0.011	500	1	500	0	0	2026-02-24 17:48:59.674445
2	MXP	Banco de Reserva Wadsworth	$	🇲🇽	0.08	0.02	0.5	0.058	500	1	500	0	0	2026-02-24 17:48:59.67443
1	JPY	Bank of Wadsworth Japan	¥	🇯🇵	0.001	-0.005	0.15	0.0067	38980.70654330466	1	500	0	0	2026-02-24 17:48:59.674424
\.


--
-- Name: bank_debts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.bank_debts_id_seq', 1, false);


--
-- Name: bank_reserve_balances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.bank_reserve_balances_id_seq', 2, true);


--
-- Name: bond_yield_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.bond_yield_history_id_seq', 112, true);


--
-- Name: forex_trades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.forex_trades_id_seq', 14, true);


--
-- Name: interbank_trades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.interbank_trades_id_seq', 1, false);


--
-- Name: player_currency_balances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.player_currency_balances_id_seq', 1, true);


--
-- Name: player_legal_tenders_player_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.player_legal_tenders_player_id_seq', 1, false);


--
-- Name: reserve_bank_bonds_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.reserve_bank_bonds_id_seq', 3, true);


--
-- Name: state_reserve_banks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.state_reserve_banks_id_seq', 8, true);


--
-- Name: bank_debts bank_debts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_debts
    ADD CONSTRAINT bank_debts_pkey PRIMARY KEY (id);


--
-- Name: bank_reserve_balances bank_reserve_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_reserve_balances
    ADD CONSTRAINT bank_reserve_balances_pkey PRIMARY KEY (id);


--
-- Name: bond_yield_history bond_yield_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bond_yield_history
    ADD CONSTRAINT bond_yield_history_pkey PRIMARY KEY (id);


--
-- Name: forex_trades forex_trades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.forex_trades
    ADD CONSTRAINT forex_trades_pkey PRIMARY KEY (id);


--
-- Name: interbank_trades interbank_trades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.interbank_trades
    ADD CONSTRAINT interbank_trades_pkey PRIMARY KEY (id);


--
-- Name: player_currency_balances player_currency_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_currency_balances
    ADD CONSTRAINT player_currency_balances_pkey PRIMARY KEY (id);


--
-- Name: player_legal_tenders player_legal_tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.player_legal_tenders
    ADD CONSTRAINT player_legal_tenders_pkey PRIMARY KEY (player_id);


--
-- Name: reserve_bank_bonds reserve_bank_bonds_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserve_bank_bonds
    ADD CONSTRAINT reserve_bank_bonds_pkey PRIMARY KEY (id);


--
-- Name: state_reserve_banks state_reserve_banks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.state_reserve_banks
    ADD CONSTRAINT state_reserve_banks_pkey PRIMARY KEY (id);


--
-- Name: ix_bank_debts_debtor_bank_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bank_debts_debtor_bank_id ON public.bank_debts USING btree (debtor_bank_id);


--
-- Name: ix_bank_debts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bank_debts_id ON public.bank_debts USING btree (id);


--
-- Name: ix_bank_reserve_balances_bank_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bank_reserve_balances_bank_id ON public.bank_reserve_balances USING btree (bank_id);


--
-- Name: ix_bank_reserve_balances_currency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bank_reserve_balances_currency_code ON public.bank_reserve_balances USING btree (currency_code);


--
-- Name: ix_bank_reserve_balances_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bank_reserve_balances_id ON public.bank_reserve_balances USING btree (id);


--
-- Name: ix_bond_yield_history_bank_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bond_yield_history_bank_id ON public.bond_yield_history USING btree (bank_id);


--
-- Name: ix_bond_yield_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bond_yield_history_id ON public.bond_yield_history USING btree (id);


--
-- Name: ix_forex_trades_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_forex_trades_id ON public.forex_trades USING btree (id);


--
-- Name: ix_forex_trades_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_forex_trades_player_id ON public.forex_trades USING btree (player_id);


--
-- Name: ix_interbank_trades_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_interbank_trades_id ON public.interbank_trades USING btree (id);


--
-- Name: ix_player_currency_balances_currency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_player_currency_balances_currency_code ON public.player_currency_balances USING btree (currency_code);


--
-- Name: ix_player_currency_balances_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_player_currency_balances_id ON public.player_currency_balances USING btree (id);


--
-- Name: ix_player_currency_balances_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_player_currency_balances_player_id ON public.player_currency_balances USING btree (player_id);


--
-- Name: ix_player_legal_tenders_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_player_legal_tenders_player_id ON public.player_legal_tenders USING btree (player_id);


--
-- Name: ix_reserve_bank_bonds_bank_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reserve_bank_bonds_bank_id ON public.reserve_bank_bonds USING btree (bank_id);


--
-- Name: ix_reserve_bank_bonds_holder_player_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reserve_bank_bonds_holder_player_id ON public.reserve_bank_bonds USING btree (holder_player_id);


--
-- Name: ix_reserve_bank_bonds_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reserve_bank_bonds_id ON public.reserve_bank_bonds USING btree (id);


--
-- Name: ix_state_reserve_banks_currency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_state_reserve_banks_currency_code ON public.state_reserve_banks USING btree (currency_code);


--
-- Name: ix_state_reserve_banks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_state_reserve_banks_id ON public.state_reserve_banks USING btree (id);


--
-- PostgreSQL database dump complete
--

\unrestrict YkOoaIcw4AGwuNvxFvYOGIeB3xhqHBqcsuO7fN7t0R7u5I0xccYQbQtpYBlnwTo

