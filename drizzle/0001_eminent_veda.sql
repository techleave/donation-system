CREATE TABLE `donors` (
	`id` text PRIMARY KEY NOT NULL,
	`prefix` text DEFAULT '' NOT NULL,
	`english_name` text NOT NULL,
	`chinese_name` text DEFAULT '' NOT NULL,
	`phone` text DEFAULT '' NOT NULL,
	`email` text NOT NULL,
	`photo_key` text,
	`user_id` text,
	`revision` integer DEFAULT 1 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `donors_email_unique` ON `donors` (`email`);--> statement-breakpoint
CREATE UNIQUE INDEX `donors_user_id_unique` ON `donors` (`user_id`);