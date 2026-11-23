#include <linux/module.h>
#include <linux/fs.h>
#include <linux/miscdevice.h>
#include <linux/io.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#define WINDOW_SIZE 0x800000UL
static void __iomem *window;
static ssize_t fw_read(struct file *f, char __user *buf, size_t count, loff_t *pos)
{
 void *tmp; size_t n;
 if (*pos < 0) return -EINVAL;
 if (*pos >= WINDOW_SIZE) return 0;
 n = min_t(size_t, count, min_t(size_t, 4096, WINDOW_SIZE - *pos));
 if (!n) return 0;
 tmp = kmalloc(n, GFP_KERNEL);
 if (!tmp) return -ENOMEM;
 memcpy_fromio(tmp, (u8 __iomem *)window + *pos, n);
 if (copy_to_user(buf, tmp, n)) { kfree(tmp); return -EFAULT; }
 kfree(tmp); *pos += n; return n;
}
static const struct file_operations ops = {
 .owner = THIS_MODULE, .read = fw_read, .llseek = default_llseek,
};
static struct miscdevice dev = {
 .minor = MISC_DYNAMIC_MINOR, .name = "ifwi_window_ro", .fops = &ops, .mode = 0400,
};
static int __init fw_init(void)
{
 int ret;
 window = ioremap(0xff800000UL, WINDOW_SIZE);
 if (!window) return -ENOMEM;
 ret = misc_register(&dev);
 if (ret) iounmap(window);
 return ret;
}
static void __exit fw_exit(void) { misc_deregister(&dev); iounmap(window); }
module_init(fw_init); module_exit(fw_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only fixed firmware window; no write or ioctl operations");
