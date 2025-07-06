-- Schema for Keg Tap management database

-- Create beers table
CREATE TABLE IF NOT EXISTS beers (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     name TEXT NOT NULL,
     abv REAL NOT NULL,
     image_path TEXT
);

-- Create taps table
CREATE TABLE IF NOT EXISTS taps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tap_id TEXT NOT NULL,
    beer_id INTEGER,
    volume REAL NOT NULL,
    full_volume REAL NOT NULL,
    flow_rate REAL NOT NULL,
    FOREIGN KEY (beer_id) REFERENCES beers (id)
);

-- Insert some sample data
INSERT INTO beers (name, abv, image_path) VALUES
                                              ('IPA', 6.5, 'beer_images/default.jpg'),
                                              ('Stout', 5.0, 'beer_images/default.jpg'),
                                              ('Pilsner', 4.2, 'beer_images/default.jpg');

INSERT INTO taps (tap_id, beer_id, volume, full_volume, flow_rate) VALUES
                                                          ('tap_1', 1, 5000, 5000, 15.0),  -- 5 liters of IPA, flowing at 15ml/sec
                                                          ('tap_2', 2, 5000, 5000, 12.0);  -- 5 liters of Stout, flowing at 12ml/sec
