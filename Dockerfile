FROM odoo:19

USER root

# Create directories and set permissions
RUN mkdir -p /var/log/odoo && chown -R odoo:odoo /var/log/odoo

# Copy configuration and addons
COPY ./config/odoo.conf /etc/odoo/odoo.conf
COPY ./addons /mnt/extra-addons

# Set permissions for Odoo user
RUN chown -R odoo:odoo /etc/odoo/odoo.conf /mnt/extra-addons

# Create a place for filestore data if not using persistent storage (though persistent is recommended)
RUN mkdir -p /var/lib/odoo && chown -R odoo:odoo /var/lib/odoo

USER odoo

EXPOSE 8069 8072

CMD ["odoo", "-c", "/etc/odoo/odoo.conf"]
