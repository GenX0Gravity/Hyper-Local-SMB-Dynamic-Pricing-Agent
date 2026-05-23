--
-- PostgreSQL database dump
--

-- Dumped from database version 15.18
-- Dumped by pg_dump version 15.18

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: citext; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;


--
-- Name: EXTENSION citext; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION citext IS 'data type for case-insensitive character strings';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: adjustment_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.adjustment_type AS ENUM (
    'percentage',
    'fixed'
);


--
-- Name: audit_action; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.audit_action AS ENUM (
    'create',
    'update',
    'delete',
    'login',
    'approve',
    'reject',
    'apply'
);


--
-- Name: business_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.business_status AS ENUM (
    'active',
    'suspended',
    'trial',
    'cancelled'
);


--
-- Name: notification_channel; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notification_channel AS ENUM (
    'email',
    'sms',
    'whatsapp',
    'push',
    'in_app'
);


--
-- Name: notification_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notification_status AS ENUM (
    'pending',
    'sent',
    'failed',
    'read'
);


--
-- Name: pricing_action_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.pricing_action_status AS ENUM (
    'pending',
    'applied',
    'reverted',
    'failed'
);


--
-- Name: pricing_rule_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.pricing_rule_type AS ENUM (
    'weather',
    'event',
    'inventory',
    'time_of_day',
    'demand',
    'footfall',
    'composite'
);


--
-- Name: subscription_plan; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.subscription_plan AS ENUM (
    'free',
    'starter',
    'growth',
    'enterprise'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'owner',
    'admin',
    'manager',
    'viewer'
);


--
-- Name: current_business_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.current_business_id() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
    SELECT NULLIF(current_setting('app.current_business_id', TRUE), '')::UUID;
$$;


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    actor_id uuid,
    entity_type character varying(50) NOT NULL,
    entity_id uuid NOT NULL,
    action public.audit_action NOT NULL,
    old_values jsonb,
    new_values jsonb,
    ip_address inet,
    user_agent character varying(512),
    request_id character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE audit_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_logs IS 'Immutable compliance trail for all tenant mutations';


--
-- Name: business_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.business_users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role public.user_role DEFAULT 'viewer'::public.user_role NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    invited_at timestamp with time zone,
    joined_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE business_users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.business_users IS 'Many-to-many: users may belong to multiple businesses';


--
-- Name: businesses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.businesses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    business_type character varying(50) NOT NULL,
    status public.business_status DEFAULT 'trial'::public.business_status NOT NULL,
    subscription_plan public.subscription_plan DEFAULT 'free'::public.subscription_plan NOT NULL,
    currency character(3) DEFAULT 'USD'::bpchar NOT NULL,
    timezone character varying(64) DEFAULT 'UTC'::character varying NOT NULL,
    whatsapp_phone character varying(20),
    whatsapp_enabled boolean DEFAULT false NOT NULL,
    settings jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE businesses; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.businesses IS 'Tenant root — each SMB subscriber';


--
-- Name: demand_predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.demand_predictions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    location_id uuid NOT NULL,
    product_id uuid NOT NULL,
    horizon_start timestamp with time zone NOT NULL,
    horizon_end timestamp with time zone NOT NULL,
    predicted_units numeric(12,4) NOT NULL,
    predicted_revenue numeric(14,2),
    confidence numeric(5,4),
    model_version character varying(50) NOT NULL,
    features jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_demand_horizon CHECK ((horizon_end > horizon_start)),
    CONSTRAINT demand_predictions_confidence_check CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))
);


--
-- Name: TABLE demand_predictions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.demand_predictions IS 'ML demand forecasts driving dynamic pricing';


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    location_id uuid NOT NULL,
    external_id character varying(255),
    name character varying(500) NOT NULL,
    description text,
    category character varying(100),
    start_at timestamp with time zone NOT NULL,
    end_at timestamp with time zone,
    impact_score numeric(5,4),
    attendance_est integer,
    source character varying(50) DEFAULT 'predicthq'::character varying NOT NULL,
    venue_name character varying(255),
    raw_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT events_impact_score_check CHECK (((impact_score IS NULL) OR ((impact_score >= (0)::numeric) AND (impact_score <= (1)::numeric))))
);


--
-- Name: footfall_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.footfall_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    location_id uuid NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    granularity character varying(20) DEFAULT 'hourly'::character varying NOT NULL,
    visitor_count integer NOT NULL,
    dwell_minutes numeric(8,2),
    conversion_rate numeric(5,4),
    source character varying(50) DEFAULT 'manual'::character varying NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT footfall_metrics_visitor_count_check CHECK ((visitor_count >= 0))
);


--
-- Name: location_products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.location_products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    location_id uuid NOT NULL,
    product_id uuid NOT NULL,
    current_price numeric(12,2) NOT NULL,
    stock_qty integer DEFAULT 0 NOT NULL,
    reorder_level integer,
    last_restocked_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT location_products_current_price_check CHECK ((current_price >= (0)::numeric)),
    CONSTRAINT location_products_stock_qty_check CHECK ((stock_qty >= 0))
);


--
-- Name: TABLE location_products; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.location_products IS 'Per-outlet price and inventory (3NF split from products)';


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    code character varying(50),
    address_line1 character varying(255),
    address_line2 character varying(255),
    city character varying(100),
    state character varying(100),
    postal_code character varying(20),
    country character(2) DEFAULT 'US'::bpchar NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    timezone character varying(64) DEFAULT 'UTC'::character varying NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    user_id uuid,
    pricing_action_id uuid,
    channel public.notification_channel NOT NULL,
    notification_type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    body text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    status public.notification_status DEFAULT 'pending'::public.notification_status NOT NULL,
    sent_at timestamp with time zone,
    read_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pricing_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pricing_actions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    location_id uuid NOT NULL,
    product_id uuid NOT NULL,
    pricing_rule_id uuid,
    demand_prediction_id uuid,
    previous_price numeric(12,2) NOT NULL,
    new_price numeric(12,2) NOT NULL,
    adjustment_pct numeric(8,4),
    reason text NOT NULL,
    status public.pricing_action_status DEFAULT 'pending'::public.pricing_action_status NOT NULL,
    triggered_by character varying(50) DEFAULT 'engine'::character varying NOT NULL,
    applied_by uuid,
    scheduled_at timestamp with time zone,
    applied_at timestamp with time zone,
    reverted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE pricing_actions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.pricing_actions IS 'Executed or pending price changes (replaces recommendations)';


--
-- Name: pricing_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pricing_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    location_id uuid,
    product_id uuid,
    name character varying(255) NOT NULL,
    rule_type public.pricing_rule_type NOT NULL,
    conditions jsonb DEFAULT '{}'::jsonb NOT NULL,
    adjustment_type public.adjustment_type NOT NULL,
    adjustment_value numeric(12,4) NOT NULL,
    priority smallint DEFAULT 100 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    valid_from timestamp with time zone,
    valid_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    business_id uuid NOT NULL,
    sku character varying(100),
    name character varying(255) NOT NULL,
    description text,
    category character varying(100),
    unit character varying(20) DEFAULT 'each'::character varying,
    cost_price numeric(12,2) NOT NULL,
    base_price numeric(12,2) NOT NULL,
    min_price numeric(12,2),
    max_price numeric(12,2),
    is_active boolean DEFAULT true NOT NULL,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_products_price_bounds CHECK (((min_price IS NULL) OR (max_price IS NULL) OR (min_price <= max_price))),
    CONSTRAINT products_base_price_check CHECK ((base_price >= (0)::numeric)),
    CONSTRAINT products_cost_price_check CHECK ((cost_price >= (0)::numeric))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email public.citext NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    phone character varying(20),
    is_active boolean DEFAULT true NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: weather_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.weather_data (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    location_id uuid NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    temperature_c numeric(5,2),
    feels_like_c numeric(5,2),
    humidity_pct numeric(5,2),
    wind_speed_ms numeric(6,2),
    condition_code character varying(50),
    condition_label character varying(100),
    precipitation_mm numeric(8,2),
    source character varying(50) DEFAULT 'openweather'::character varying NOT NULL,
    raw_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: business_users business_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_users
    ADD CONSTRAINT business_users_pkey PRIMARY KEY (id);


--
-- Name: businesses businesses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT businesses_pkey PRIMARY KEY (id);


--
-- Name: demand_predictions demand_predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demand_predictions
    ADD CONSTRAINT demand_predictions_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: footfall_metrics footfall_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.footfall_metrics
    ADD CONSTRAINT footfall_metrics_pkey PRIMARY KEY (id);


--
-- Name: location_products location_products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_products
    ADD CONSTRAINT location_products_pkey PRIMARY KEY (id);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: pricing_actions pricing_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_pkey PRIMARY KEY (id);


--
-- Name: pricing_rules pricing_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_rules
    ADD CONSTRAINT pricing_rules_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: business_users uq_business_users_membership; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_users
    ADD CONSTRAINT uq_business_users_membership UNIQUE (business_id, user_id);


--
-- Name: businesses uq_businesses_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT uq_businesses_slug UNIQUE (slug);


--
-- Name: events uq_events_location_external; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT uq_events_location_external UNIQUE (location_id, external_id, source);


--
-- Name: footfall_metrics uq_footfall_location_time_gran; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.footfall_metrics
    ADD CONSTRAINT uq_footfall_location_time_gran UNIQUE (location_id, recorded_at, granularity, source);


--
-- Name: location_products uq_location_products; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_products
    ADD CONSTRAINT uq_location_products UNIQUE (location_id, product_id);


--
-- Name: locations uq_locations_business_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT uq_locations_business_code UNIQUE (business_id, code);


--
-- Name: products uq_products_business_sku; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT uq_products_business_sku UNIQUE (business_id, sku);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: weather_data uq_weather_location_recorded; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weather_data
    ADD CONSTRAINT uq_weather_location_recorded UNIQUE (location_id, recorded_at, source);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: weather_data weather_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weather_data
    ADD CONSTRAINT weather_data_pkey PRIMARY KEY (id);


--
-- Name: idx_audit_logs_actor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_actor ON public.audit_logs USING btree (actor_id, created_at DESC) WHERE (actor_id IS NOT NULL);


--
-- Name: idx_audit_logs_business_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_business_time ON public.audit_logs USING btree (business_id, created_at DESC);


--
-- Name: idx_audit_logs_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_entity ON public.audit_logs USING btree (entity_type, entity_id, created_at DESC);


--
-- Name: idx_business_users_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_business_users_business ON public.business_users USING btree (business_id);


--
-- Name: idx_business_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_business_users_role ON public.business_users USING btree (business_id, role);


--
-- Name: idx_business_users_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_business_users_user ON public.business_users USING btree (user_id);


--
-- Name: idx_businesses_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_businesses_created_at ON public.businesses USING btree (created_at DESC);


--
-- Name: idx_businesses_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_businesses_status ON public.businesses USING btree (status);


--
-- Name: idx_demand_predictions_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_demand_predictions_business ON public.demand_predictions USING btree (business_id);


--
-- Name: idx_demand_predictions_location_horizon; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_demand_predictions_location_horizon ON public.demand_predictions USING btree (location_id, horizon_start DESC);


--
-- Name: idx_demand_predictions_product_horizon; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_demand_predictions_product_horizon ON public.demand_predictions USING btree (product_id, horizon_start);


--
-- Name: idx_events_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_category ON public.events USING btree (location_id, category);


--
-- Name: idx_events_location_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_location_start ON public.events USING btree (location_id, start_at);


--
-- Name: idx_events_start_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_start_at ON public.events USING btree (start_at);


--
-- Name: idx_footfall_location_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_footfall_location_time ON public.footfall_metrics USING btree (location_id, recorded_at DESC);


--
-- Name: idx_footfall_recorded_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_footfall_recorded_at ON public.footfall_metrics USING btree (recorded_at DESC);


--
-- Name: idx_location_products_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_location_products_location ON public.location_products USING btree (location_id);


--
-- Name: idx_location_products_low_stock; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_location_products_low_stock ON public.location_products USING btree (location_id, stock_qty) WHERE (stock_qty <= 10);


--
-- Name: idx_location_products_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_location_products_product ON public.location_products USING btree (product_id);


--
-- Name: idx_locations_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_business ON public.locations USING btree (business_id);


--
-- Name: idx_locations_business_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_business_active ON public.locations USING btree (business_id) WHERE (is_active = true);


--
-- Name: idx_locations_geo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_locations_geo ON public.locations USING btree (latitude, longitude);


--
-- Name: idx_notifications_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_business ON public.notifications USING btree (business_id, created_at DESC);


--
-- Name: idx_notifications_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_pending ON public.notifications USING btree (status, created_at) WHERE (status = 'pending'::public.notification_status);


--
-- Name: idx_notifications_user_unread; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_user_unread ON public.notifications USING btree (user_id, created_at DESC) WHERE ((read_at IS NULL) AND (status = 'sent'::public.notification_status));


--
-- Name: idx_pricing_actions_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_actions_business ON public.pricing_actions USING btree (business_id, created_at DESC);


--
-- Name: idx_pricing_actions_location_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_actions_location_product ON public.pricing_actions USING btree (location_id, product_id, created_at DESC);


--
-- Name: idx_pricing_actions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_actions_status ON public.pricing_actions USING btree (business_id, status) WHERE (status = 'pending'::public.pricing_action_status);


--
-- Name: idx_pricing_rules_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_rules_business ON public.pricing_rules USING btree (business_id);


--
-- Name: idx_pricing_rules_business_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_rules_business_active ON public.pricing_rules USING btree (business_id, is_active, priority) WHERE (is_active = true);


--
-- Name: idx_pricing_rules_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_rules_location ON public.pricing_rules USING btree (location_id) WHERE (location_id IS NOT NULL);


--
-- Name: idx_pricing_rules_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pricing_rules_type ON public.pricing_rules USING btree (business_id, rule_type);


--
-- Name: idx_products_business; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_business ON public.products USING btree (business_id);


--
-- Name: idx_products_business_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_business_active ON public.products USING btree (business_id) WHERE (is_active = true);


--
-- Name: idx_products_business_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_business_category ON public.products USING btree (business_id, category);


--
-- Name: idx_users_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_active ON public.users USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_weather_location_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_weather_location_time ON public.weather_data USING btree (location_id, recorded_at DESC);


--
-- Name: idx_weather_recorded_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_weather_recorded_at ON public.weather_data USING btree (recorded_at DESC);


--
-- Name: businesses trg_businesses_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_businesses_updated_at BEFORE UPDATE ON public.businesses FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: locations trg_locations_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_locations_updated_at BEFORE UPDATE ON public.locations FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: pricing_rules trg_pricing_rules_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pricing_rules_updated_at BEFORE UPDATE ON public.pricing_rules FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: products trg_products_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: users trg_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: audit_logs audit_logs_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: audit_logs audit_logs_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: business_users business_users_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_users
    ADD CONSTRAINT business_users_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: business_users business_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_users
    ADD CONSTRAINT business_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: demand_predictions demand_predictions_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demand_predictions
    ADD CONSTRAINT demand_predictions_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: demand_predictions demand_predictions_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demand_predictions
    ADD CONSTRAINT demand_predictions_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: demand_predictions demand_predictions_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.demand_predictions
    ADD CONSTRAINT demand_predictions_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: events events_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: footfall_metrics footfall_metrics_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.footfall_metrics
    ADD CONSTRAINT footfall_metrics_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: location_products location_products_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_products
    ADD CONSTRAINT location_products_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: location_products location_products_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location_products
    ADD CONSTRAINT location_products_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: locations locations_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: notifications notifications_pricing_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pricing_action_id_fkey FOREIGN KEY (pricing_action_id) REFERENCES public.pricing_actions(id) ON DELETE SET NULL;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: pricing_actions pricing_actions_applied_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_applied_by_fkey FOREIGN KEY (applied_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: pricing_actions pricing_actions_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: pricing_actions pricing_actions_demand_prediction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_demand_prediction_id_fkey FOREIGN KEY (demand_prediction_id) REFERENCES public.demand_predictions(id) ON DELETE SET NULL;


--
-- Name: pricing_actions pricing_actions_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: pricing_actions pricing_actions_pricing_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_pricing_rule_id_fkey FOREIGN KEY (pricing_rule_id) REFERENCES public.pricing_rules(id) ON DELETE SET NULL;


--
-- Name: pricing_actions pricing_actions_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_actions
    ADD CONSTRAINT pricing_actions_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: pricing_rules pricing_rules_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_rules
    ADD CONSTRAINT pricing_rules_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: pricing_rules pricing_rules_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_rules
    ADD CONSTRAINT pricing_rules_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: pricing_rules pricing_rules_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pricing_rules
    ADD CONSTRAINT pricing_rules_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: products products_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(id) ON DELETE CASCADE;


--
-- Name: weather_data weather_data_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weather_data
    ADD CONSTRAINT weather_data_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id) ON DELETE CASCADE;


--
-- Name: audit_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: business_users; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.business_users ENABLE ROW LEVEL SECURITY;

--
-- Name: businesses; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.businesses ENABLE ROW LEVEL SECURITY;

--
-- Name: demand_predictions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.demand_predictions ENABLE ROW LEVEL SECURITY;

--
-- Name: location_products; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.location_products ENABLE ROW LEVEL SECURITY;

--
-- Name: locations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.locations ENABLE ROW LEVEL SECURITY;

--
-- Name: notifications; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

--
-- Name: pricing_actions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.pricing_actions ENABLE ROW LEVEL SECURITY;

--
-- Name: pricing_rules; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.pricing_rules ENABLE ROW LEVEL SECURITY;

--
-- Name: products; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

--
-- Name: audit_logs tenant_isolation_audit_logs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_audit_logs ON public.audit_logs USING ((business_id = public.current_business_id()));


--
-- Name: demand_predictions tenant_isolation_demand_predictions; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_demand_predictions ON public.demand_predictions USING ((business_id = public.current_business_id()));


--
-- Name: locations tenant_isolation_locations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_locations ON public.locations USING ((business_id = public.current_business_id()));


--
-- Name: notifications tenant_isolation_notifications; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_notifications ON public.notifications USING ((business_id = public.current_business_id()));


--
-- Name: pricing_actions tenant_isolation_pricing_actions; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_pricing_actions ON public.pricing_actions USING ((business_id = public.current_business_id()));


--
-- Name: pricing_rules tenant_isolation_pricing_rules; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_pricing_rules ON public.pricing_rules USING ((business_id = public.current_business_id()));


--
-- Name: products tenant_isolation_products; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_products ON public.products USING ((business_id = public.current_business_id()));


--
-- PostgreSQL database dump complete
--

\unrestrict 16mDpFL3GW1AgQfVG54qbdeMyJoCyvGuElRNdMkP1dEuqVnb8RNbKyGha0FkmNj

