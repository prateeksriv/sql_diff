CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying(255),
    email character varying(255)
);

ALTER TABLE ONLY public.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);

CREATE TABLE public.posts (
    id integer NOT NULL,
    user_id integer,
    content text,
    created_at timestamp without time zone DEFAULT now()
);

ALTER TABLE ONLY public.posts ADD CONSTRAINT posts_pkey PRIMARY KEY (id);

-- posts_user_id_fkey is removed

ALTER TABLE ONLY public.users ADD CONSTRAINT users_email_unique UNIQUE (email);
