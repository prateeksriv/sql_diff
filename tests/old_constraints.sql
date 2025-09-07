CREATE TABLE public.users (
    id integer NOT NULL,
    name character varying(255)
);

ALTER TABLE ONLY public.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);

CREATE TABLE public.posts (
    id integer NOT NULL,
    user_id integer,
    content text
);

ALTER TABLE ONLY public.posts ADD CONSTRAINT posts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.posts ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);

ALTER TABLE ONLY public.users ADD CONSTRAINT users_name_unique UNIQUE (name);
